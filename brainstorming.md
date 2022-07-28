# nlp brainstorming

## comparing language models

* kindred
* scispacy
* biospacy

How well do they recognize entities from the following datasets:

* Gene, therapy, disease normalizer: difference classes of terms
* DGIdb: drug and gene names
* MetaKB: all subject/object/object qualifier terms

## fda data

Extract entity relationships from indications.

Replicate chembl toxicology/box warning paper? https://pubs.acs.org/doi/10.1021/acs.chemrestox.0c00296

## ML publication classification/topic modeling

1) Identify specific sentence topics of interest -- eg, data leakage prevention ("a test/train split was performed") and construct topic vectors

2) perform classification to determine presence

Use existing data leakage papers to help construct corpus
