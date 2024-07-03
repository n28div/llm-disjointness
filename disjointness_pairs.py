import rdflib
from collections import defaultdict
from itertools import combinations, chain, product
import requests
from tqdm import tqdm
from tqdm.contrib.concurrent import thread_map
import csv
import argparse

class ClassesPair():
  def __init__(self, classes):
    super().__init__()
    self.L = {f"{c1}__{c2}": None for c1, c2 in combinations(classes, 2)}
    
  def __getitem__(self, k):
    c1, c2 = sorted(k)
    return self.L[f"{c1}__{c2}"]
  
  def __setitem__(self, k, v):
    c1, c2 = sorted(k)
    self.L[f"{c1}__{c2}"] = v

  def items(self):
    for k, v in self.L.items():
      c1, c2 = k.split("__")
      yield c1, c2, v

  def __len__(self):
    return len(self.L)

  def disjoints(self):
    return (
      tuple(map(rdflib.URIRef, k.split("__"))) 
      for k, v in self.L.items() if v is True
    )

  def joint(self):
    return (
      tuple(map(rdflib.URIRef, k.split("__"))) 
      for k, v in self.L.items() if v is False
    )

  def unknown(self):
    return (
      tuple(map(rdflib.URIRef, k.split("__"))) 
      for k, v in self.L.items() if v is None
    )

def subclass_traverse(node, g):
  for n, _, _ in g.triples((None, rdflib.RDFS.subClassOf, node)):
    yield n

RDF_Description = rdflib.URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#Description")

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("-o", "--ontology", type=str, required=True)
argument_parser.add_argument("-s", "--sparql", type=str, default="https://dbpedia.org/sparql")
argument_parser.add_argument("--output", type=str, required=True)

if __name__ == "__main__":
  args = argument_parser.parse_args()

  graph = rdflib.Graph().parse(args.ontology)

  # collect all the classes
  classes = chain(
    graph.subjects(rdflib.RDF.type, rdflib.OWL.Class),
    graph.subjects(rdflib.RDF.type, RDF_Description)
  )

  # initialize L
  L = ClassesPair(classes)

  # initialize L with disjointness statements from the ontology
  for c1, c2 in graph.subject_objects(rdflib.OWL.disjointWith):
    L[c1, c2] = True
    
    # take the subclasses of c1 and c2
    c1_subclasses = sorted(graph.transitiveClosure(subclass_traverse, c1))
    c2_subclasses = sorted(graph.transitive_subjects(subclass_traverse, c2))

    # since c1 and c2 are disjoint, so are all their pairwise subclasses  
    for c1_sub, c2_sub in product(c1_subclasses, c2_subclasses):
      L[c1_sub, c2_sub] = True

  # all classes that have common subclasses are not disjoint
  unknowns = list(L.unknown())
  for c1, c2 in unknowns:
    c1_subclasses = set(graph.transitiveClosure(subclass_traverse, c1))
    c2_subclasses = set(graph.transitive_subjects(subclass_traverse, c2))

    if len(c1_subclasses.intersection(c2_subclasses)) > 0:
      L[c1, c2] = True

  # query for common instances
  def query_dbpedia(c1, c2):
    ask = requests.get(args.sparql, 
      headers={ 'Accept': 'application/json' }, 
      params={ 'query': 'ASK { ?a a <%s>, <%s> . }' % (c1, c2),
    })

    if ask.json()["boolean"]:
      L[c1, c2] = False

  unknowns = list(L.unknown())
  thread_map(lambda a: query_dbpedia(*a), unknowns)

  with open(args.output, 'w') as csvfile:
    writer = csv.writer(csvfile)
    for c1, c2, v in L.items():
      writer.writerow([c1, c2, v])