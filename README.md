# Running Disjointness Inference on DBPedia
This guide details the steps to set up and run our scripts for inferring disjointness axioms in the DBPedia ontology, based on the methodology described in our paper.

## Introduction
Ontologies often lack explicit disjointness declarations between classes, despite their usefulness for sophisticated reasoning and consistency-checking in Knowledge Graphs. In our study, we explore the potential of Large Language Models (LLMs) to enrich ontologies by identifying and asserting class disjointness axioms. Our approach leverages LLMs through prompt engineering to classify ontological disjointness, validated on the DBpedia ontology.

## Prerequisites
To efficiently run the scripts, a local version of DBPedia is required for faster querying.

## Setup Instructions

### Step 1: Download DBPedia ABox

  1. Download the DBPedia ABox from [DBPedia Databus](https://databus.dbpedia.org/dbpedia/mappings/instance-types/). The `en,specific` version is recommended.
  2. Note: The downloaded ABox contains information only on `rdf:type` assertions. To compute the transitive closure according to the ontology (including subclass assertions), an external reasoner is needed. This step, while not strictly necessary, significantly speeds up querying the local triple store.

### Step 2: Compute the Transitive Closure
Use Jena RIOT to compute the closure:
```bash
$ riot --output=TTL <path_to_dbo_ontology.owl> > <path_to_output_inferred.ttl>
```

### Step 3: Create a Triple Store

  1. Build the database:
```bash
$ tdb2.tdbloader --loc=<db_location> <path_to_inferred.ttl>
```

  2. Launch the triple store with Apache Jena Fuseki:
```bash
$ fuseki-server --port 8888 --loc=dbpediatdb /ds
```
The SPARQL endpoint will be available at `http://localhost:8888/#/dataset/ds/query`.

## Running the Scripts

### Step 4: Compute the L Pairs
Run the following command to compute the L pairs:
```bash
$ python disjointness_pairs.py -o <path_to_dbpedia_ontology> -s <sparql_endpoint> --output <output_csv_path>
```
For faster execution, ensure the ontology is in N-Triples format.

### Step 5: Infer Disjointness Axioms
Use the LLM to infer disjointness axioms:
```bash
$ python infer_disjointness_axioms.py -p <csv_path_of_disjointness_pairs> -o <path_to_dbpedia_ontology> --output <output_csv_path_for_disjoint_classes>
```
Note: This process can be time-consuming. In our experiments, it took approximately 6 hours to find over 500k axioms.

### Step 6: Prune the Axioms
Prune redundant axioms with:
```bash
$ python prune_disjointness_axioms.py -d <csv_path_for_disjoint_classes> -o <path_to_dbpedia_ontology> --output <output_ontology_ntriples_format>
```
In our experiments, we reduced the axioms to approximately 170k.

## Conclusion
Following these steps, you can efficiently infer and prune disjointness axioms in the DBPedia ontology, leveraging LLMs for ontology enhancement. For further details, refer to the methodology described in our paper.
 
This README provides a comprehensive guide for setting up and executing the scripts required to infer and prune disjointness axioms in the DBPedia ontology. For additional information, please refer to our research paper.