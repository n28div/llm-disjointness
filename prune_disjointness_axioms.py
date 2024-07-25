import argparse
import rdflib
import z3
import pandas as pd
from tqdm import tqdm

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("-d", "--disjointness-pairs", type=str, required=True)
argument_parser.add_argument("-o", "--ontology", type=str, required=True)
argument_parser.add_argument("--output", type=str, required=True)

if __name__ == "__main__":
    args = argument_parser.parse_args()
    
    graph = rdflib.Graph().parse(args.ontology)
    print("Loaded ontology")

    # Compute the KB
    classes = list(graph.subjects(predicate=rdflib.RDF.type, object=rdflib.OWL.Class))
    variables = { c: z3.Bool(str(c)) for c in classes }
    
    K = []
    for s, _, o in graph.triples((None, rdflib.RDFS.subClassOf, None)):
        if s not in variables:
            variables[s] = z3.Bool(str(s))
        if o not in variables:
            variables[o] = z3.Bool(str(o))

        K.append(z3.Implies(variables[s], variables[o]))

    for s, _, o in graph.triples((None, rdflib.OWL.disjointWith, None)):
        if s not in variables:
            variables[s] = z3.Bool(str(s))
        if o not in variables:
            variables[o] = z3.Bool(str(o))

        K.append(z3.Not(z3.And(variables[s], variables[o])))
    print("Computed KB")

    # Compute D*
    D_star_df = pd.read_csv(args.disjointness_pairs)
    print(f"Initial disjoint axioms: {D_star_df.disjoint.sum()}")

    D_star = K.copy()
    for _, row in tqdm(D_star_df[D_star_df.disjoint].iterrows(), total=D_star_df.shape[0]):
        s = rdflib.URIRef(row.c1)
        o = rdflib.URIRef(row.c2)

        if s not in variables:
            variables[s] = z3.Bool(str(s))
        if o not in variables:
            variables[o] = z3.Bool(str(o))

        D_star.append(z3.Not(z3.And(variables[s], variables[o])))
    
    # Prunse axioms use z3 sat solver
    g  = z3.Goal()
    g.add(*D_star)
    tactic  = z3.Then(z3.Tactic('simplify'), z3.Tactic('solve-eqs'))
    simplified = tactic(g)

    disjointness_axioms = [(x.arg(0).arg(0), x.arg(0).arg(1)) for x in simplified[0] if x.num_args() == 1]
    disjointness_axioms = [(rdflib.URIRef(str(a)), rdflib.URIRef(str(b))) for a, b in disjointness_axioms]

    print("After pruning:", len(disjointness_axioms))

    for a, b in disjointness_axioms:
        graph.add((a, rdflib.OWL.disjointWith, b))

    graph.serialize(args.output, format="nt", encoding="utf-8")