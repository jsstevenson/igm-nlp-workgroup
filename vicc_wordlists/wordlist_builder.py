"""Construct word lists from VICC normalizers."""
import csv
from enum import Enum
from typing import Tuple, Dict, List
import logging

from tqdm import tqdm
import boto3
from boto3.dynamodb.conditions import Key
from therapy.database import Database as TherapyDatabase
from disease.database import Database as DiseaseDatabase
from gene.database import Database as GeneDatabase


ddb = boto3.resource("dynamodb")
logger = logging.getLogger("wordlist_builder")


def normalize_id(concept_id: str, concepts) -> Dict:
    """Look up record for normalized reference"""
    response = concepts.query(
        KeyConditionExpression=Key("label_and_type").eq(
            f"{concept_id}##merger"
        )
    )
    try:
        return response["Items"][0]
    except IndexError:
        logger.error(f"Failed to normalize term: {concept_id}")
        raise IndexError


TermResponse = Tuple[str, Tuple[str, List[str]], Tuple[str, List[str]]]


def get_therapy_term(record: Dict) -> TermResponse:
    """Build therapy term set"""
    key = record["concept_id"]
    label = record["label"]

    min_terms = set(
        record.get("aliases", []) + record.get("trade_names", [])
    )
    min_terms.add(label)
    xrefs = set(record.get("xrefs", []))
    assoc_with = set(record.get("associated_with", []))

    term_complete = (label, list(min_terms.union(xrefs).union(assoc_with)))
    term_min = (label, list(min_terms))
    return (key, term_complete, term_min)


def get_gene_term(record: Dict) -> TermResponse:
    """Build gene term set"""
    key = record["concept_id"]
    symbol = record["symbol"]

    min_terms = set(
        record.get("aliases", []) + record.get("previous_symbols", [])
    )
    min_terms.add(symbol)
    if "label" in record:
        min_terms.add(record["label"])
    xrefs = set(record.get("xrefs", []))
    assoc_with = set(record.get("associated_with", []))

    term_complete = (symbol, list(min_terms.union(xrefs).union(assoc_with)))
    term_min = (symbol, list(min_terms))
    return (key, term_complete, term_min)


def get_disease_term(record: Dict) -> TermResponse:
    """Build disease term set"""
    key = record["concept_id"]
    label = record["label"]
    min_terms = set(record.get("aliases", []))
    min_terms.add(label)
    xrefs = set(record.get("xrefs", []))
    assoc_with = set(record.get("associated_with", []))

    term_complete = (label, list(min_terms.union(xrefs).union(assoc_with)))
    term_min = (label, list(min_terms))
    return (key, term_complete, term_min)


class ConceptType(str, Enum):
    GENE = "gene"
    DRUG = "drug"
    DISEASE = "disease"


def get_term(normalized_record: Dict, concept_type: ConceptType):
    if concept_type == ConceptType.DRUG:
        return get_therapy_term(normalized_record)
    elif concept_type == ConceptType.DISEASE:
        return get_disease_term(normalized_record)
    elif concept_type == ConceptType.GENE:
        return get_gene_term(normalized_record)
    else:
        raise Exception("Unrecognized concept type")


def build_list(concept_type: ConceptType):
    wordlist_complete = {}
    wordlist_min = {}
    if concept_type == ConceptType.DRUG:
        concepts_table = TherapyDatabase().therapies
    elif concept_type == ConceptType.DISEASE:
        concepts_table = DiseaseDatabase().diseases
    elif concept_type == ConceptType.GENE:
        concepts_table = GeneDatabase().genes
    else:
        raise Exception("Unrecognized concept type")
    est_item_count = concepts_table.item_count
    pbar = tqdm(total=est_item_count)

    last_eval_key = None
    while True:
        if last_eval_key:
            response = concepts_table.scan(ExclusiveStartKey=last_eval_key)
        else:
            response = concepts_table.scan()
        records = response["Items"]
        for record in records:
            if record["item_type"] != "identity":
                continue
            if concept_type == ConceptType.DRUG and "label" not in record:
                continue
            elif concept_type == ConceptType.DISEASE and "label" not in record:
                continue
            elif concept_type == ConceptType.GENE and "symbol" not in record:
                continue
            if "merge_ref" in record:
                if record["merge_ref"] not in wordlist_complete:
                    try:
                        normalized_record = normalize_id(
                            record["merge_ref"], concepts_table
                        )
                    except IndexError:
                        continue  # shouldn't happen though
                    key, term_complete, term_min = get_term(
                        normalized_record, concept_type
                    )
                    wordlist_complete[key] = term_complete
                    wordlist_min[key] = term_min
            else:
                key, term_complete, term_min = get_term(record, concept_type)
                wordlist_complete[key] = term_complete
                wordlist_min[key] = term_min
        pbar.update(len(response["Items"]))
        last_eval_key = response.get("LastEvaluatedKey")
        if not last_eval_key:
            break
    pbar.close()
    with open(f"terms_{concept_type.value}s_full.tsv", "w") as f:
        writer = csv.writer(f)
        for key, value in wordlist_complete.items():
            row = [key, value[0], "|".join(value[1])]
            writer.writerow(row)
    with open(f"terms_{concept_type.value}s_min.tsv", "w") as f:
        writer = csv.writer(f)
        for key, value in wordlist_min.items():
            row = [key, value[0], "|".join(value[1])]
            writer.writerow(row)


if __name__ == '__main__':
    # print("Constructing disease list...")
    # build_list(ConceptType.DISEASE)
    print("Constructing gene list...")
    build_list(ConceptType.GENE)
    # print("Constructing drug list...")
    # build_list(ConceptType.DRUG)
