import rdflib
from itertools import combinations


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

def superclass_traverse(node, g):
  for n, _, _ in g.triples((node, rdflib.RDFS.subClassOf, None)):
    yield n