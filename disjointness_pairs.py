import rdflib
from collections import defaultdict
from itertools import combinations, chain, product
import requests
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map
import csv
import argparse

from utils import ClassesPair, subclass_traverse

RDF_Description = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Description")

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("-o", "--ontology", type=str, required=True)
argument_parser.add_argument("-s", "--sparql", type=str, default="https://dbpedia.org/sparql")
argument_parser.add_argument("--output", type=str, required=True)

if __name__ == "__main__":
  args = argument_parser.parse_args()

  graph = rdflib.Graph().parse(args.ontology)
  print("Loaded the ontology")

  # collect all the classes
  classes = chain(
    graph.subjects(rdflib.RDF.type, rdflib.OWL.Class),
    graph.subjects(rdflib.RDF.type, RDF_Description)
  )

  # initialize L
  L = ClassesPair(classes)

  # initialize L with disjointness statements from the ontology
  for c1, c2 in graph.subject_objects(rdflib.OWL.disjointWith):
    L[c1, c2] = (True, "ontologically disjoint")
    
    # take the subclasses of c1 and c2
    c1_subclasses = sorted(graph.transitiveClosure(subclass_traverse, c1))
    c2_subclasses = sorted(graph.transitive_subjects(subclass_traverse, c2))

    # since c1 and c2 are disjoint, so are all their pairwise subclasses  
    for c1_sub, c2_sub in product(c1_subclasses, c2_subclasses):
      L[c1_sub, c2_sub] = (True, "subclass of ontologically disjoint")
  print("Derived disjoint axioms from the ontology")

  # all classes that have common subclasses are not disjoint
  unknowns = list(L.unknown())
  for c1, c2 in unknowns:
    c1_subclasses = set(graph.transitiveClosure(subclass_traverse, c1))
    c2_subclasses = set(graph.transitive_subjects(subclass_traverse, c2))

    if len(c1_subclasses.intersection(c2_subclasses)) > 0:
      L[c1, c2] = (False, "common subclasses")
  print("Derived non-disjointness axioms from the ontology")

  # query for common instances
  def query_endpoint(c1, c2):
    try:
      ask = requests.post(args.sparql, 
        headers={ 'Accept': 'application/json' }, 
        params={ 'query': 'ASK { ?a a <%s>, <%s> . }' % (c1, c2),
      })

      if ask.json()["boolean"]:
        L[c1, c2] = (False, "common instance")
    except:
      pass

  unknowns = list(L.unknown())
  thread_map(lambda a: query_endpoint(*a), unknowns)
  print("Derived material disjointness from the data")
  
  with open(args.output, 'w') as csvfile:
    writer = csv.writer(csvfile)
    for c1, c2, v in L.items():
      writer.writerow([c1, c2, v])