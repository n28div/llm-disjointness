
# Running on DBPedia

In order to run the script on DBPedia, you need a local version of DBPedia, for faster querying.

This can be done by downloading the DBPedia ABox from https://databus.dbpedia.org/dbpedia/mappings/instance-types/. Generally, the `en,specific` version is the most suited one.
Note that the ABox downloaded only contains information on the `rdf:type` assertions. To compute the transitive closure according to the ontology (i.e. also assert types from subclasses) an external reasoner needs to be used. This step is not strictly required but querying the local triple store will be significantly faster without including a reasoner in each query.

One possible way is to use Jena RIOT to compute the closure, using

```
$ riot --output=TTL <path to dbpedia.owl> > <path to output inferred.ttl>
```

Now, a triple store can be created. We will use fuseki.

First, build the DB with

```
$ tdb2.tdbloader --loc=<db location> <path to inferred.ttl>
```

and then launch the triple store with

```
$ fuseki-server --port 8888 --loc=dbpediatdb /ds
```

the sparql endpoint will be at http://localhost:8888/#/dataset/ds/query.

## Compute the $L$ pairs
Run 

```
$ python disjointness_pairs.py -o <path to dbpedia ontology> -s <sparql endpoint> --output <output to csv path>
```

note that if the ontology in in N-triples format, it will be much faster.

## Compute the disjointness axioms

You can infer the disjointness axioms using the LLM with 

```
$ python infer_disjointness_axioms.py -p <csv path of disjointness pairs> -o <dbpedia ontology path> --output <output to csv path for disjoint classes>
```

this can take long. In the experiments we performed, it took roughly 6 hours to find more than 500k axioms.

## Prune the axioms

You can prune the redundant axioms with

```
$ python prune_disjointness_axioms.py -d <csv path for disjoint classes> -o <dbpedia ontology path> --output <output ontology in ntriples format>
```

in our experiments, we reduce the axioms to ~170k.