from .retriever import retrieve
from .generator import generate
from .rare_disease_lookup import lookup as rare_lookup


def run(query: str) -> dict:
    policy_docs = retrieve(query)
    rare_matches = rare_lookup(query)
    return generate(query, policy_docs, rare_matches)
