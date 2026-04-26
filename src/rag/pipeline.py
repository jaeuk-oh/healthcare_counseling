from .retriever import retrieve
from .generator import generate


def run(query: str) -> dict:
    policy_docs = retrieve(query)
    return generate(query, policy_docs)
