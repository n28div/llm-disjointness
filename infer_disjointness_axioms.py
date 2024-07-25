import os
os.environ["VLLM_ATTENTION_BACKEND"] = "FLASHINFER"
os.environ["VLLM_CONFIGURE_LOGGING"] = "0"
os.environ["VLLM_LOGGING_LEVEL"] = "1000"

import argparse
import pandas as pd
import rdflib
from vllm import LLM, SamplingParams
from random import random
from tqdm import tqdm
import time
from itertools import product
import re

from utils import ClassesPair, subclass_traverse, superclass_traverse

SYSTEM_PROMPTS = {
    "naive": "Answer only \"yes\" or \"no\".",
    "task_description": "This is a question about ontological disjointness, answer only with \"yes\" or \"no\"",
    "few_shot": "This is a question about ontological disjointness, answer only with \"yes\" or \"no\"\nExamples of disjoint are: 'person' and 'file system', 'tower' and 'person', 'place' and 'agent', 'continent' and 'sea', 'baseball league' and 'bowling league', 'planet' and 'star'.\nExamples of not disjoint are: 'basketball player' and 'baseball player', 'means of transportation' and 'reptile', 'garden' and 'historic place', 'president' and 'beauty queen', 'castle' and 'prison'.",
}

PROMPT = {
    "can_a_question": ("Can a %s be a %s?", lambda a: False if re.match(r"^\s*[Yy]es", a) else True),
    "are_disjoint": ("Is the class %s disjoint from %s?", lambda a: True if re.match(r"^\s*[Yy]es", a) else False)
}

LLMS_MAP = {
    "meta-llama/Meta-Llama-3-8B-Instruct": "<|start_header_id|>system<|end_header_id|>\n\n%s<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n%s\n<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
    "google/gemma-2-9b-it": "<start_of_turn>user\n%s\n%s<end_of_turn>\n<start_of_turn>model\n",
    "mistralai/Mistral-7B-Instruct-v0.3": "[INST] %s \n%s [/INST]",
    "Qwen/Qwen2-7B-Instruct": "{{ if .System }}<|im_start|>system\n %s<|im_end|>\n<|im_start|>user\n%s<|im_end|>\n<|im_start|>assistant\n",

}

argument_parser = argparse.ArgumentParser()
argument_parser.add_argument("-p", "--pairs", type=str, required=True)
argument_parser.add_argument("-o", "--ontology", type=str, required=True)
argument_parser.add_argument("--output", type=str, required=True)
argument_parser.add_argument("-llm", "--llm", type=str, required=False, default="google/gemma-2-9b-it", choices=LLMS_MAP.keys())
argument_parser.add_argument("--system", type=str, default="task_description", choices=SYSTEM_PROMPTS.keys())
argument_parser.add_argument("--prompt", type=str, default="can_a_question", choices=PROMPT.keys())

if __name__ == "__main__":
    args = argument_parser.parse_args()
    start_t = time.time()
    
    graph = rdflib.Graph().parse(args.ontology)
    print("Loaded ontology")

    pairs = pd.read_csv(args.pairs, header=0, names=["c1", "c2", "disjoint"])
    pairs["reason"] = pairs.disjoint.apply(lambda x: x if pd.isna(x) else eval(x)[1])
    pairs["disjoint"] = pairs.disjoint.apply(lambda x: x if pd.isna(x) else eval(x)[0])
    
    unknown = pairs[pairs.disjoint.isna()].set_index(["c1", "c2"])

    sampling_params = SamplingParams(temperature=0.0)
    llm = LLM(model=args.llm, quantization="fp8")
    print("Loaded LLM")

    llm_template = LLMS_MAP[args.llm]
    sp = SYSTEM_PROMPTS[args.system]
    prompt, prompt_fn = PROMPT[args.prompt]

    pbar = tqdm(total=unknown.shape[0])
    try:
        while unknown.disjoint.isna().sum() > 0:
            # select (D1, D2)
            idx = unknown[unknown.disjoint.isna()].sample(1).index[0]
            d1, d2 = idx
        
            d1_name = d1.replace("http://dbpedia.org/ontology/", "")
            d2_name = d2.replace("http://dbpedia.org/ontology/", "")
            
            p = [llm_template % (sp, prompt % (d1_name, d2_name))]
            outputs = llm.generate(p, sampling_params, use_tqdm=False)
            
            disjoint = prompt_fn(outputs[0].outputs[0].text)
            
            unknown.loc[(d1, d2), "disjoint"] = disjoint
            updated = 1

            # traverse fn
            traverse_fn = subclass_traverse if disjoint else superclass_traverse
            c1s = graph.transitiveClosure(traverse_fn, rdflib.URIRef(d1))
            c2s = graph.transitiveClosure(traverse_fn, rdflib.URIRef(d2))
            for c1, c2 in product(c1s, c2s):
                unknown.loc[(str(c1), str(c2)), "disjoint"] = disjoint
                updated += 1

            pbar.update(updated)
    except KeyboardInterrupt:
        pass

    end_t = time.time()
    print(f"Finished in {end_t - start_t}s")

    unknown.to_csv(args.output)