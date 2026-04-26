import os
import chromadb
from openai import OpenAI

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return client.get_collection("policies")


def retrieve(query: str) -> list[dict]:
    """top_k = 전체 문서 수 → 모든 정책 항상 반환"""
    collection = get_collection()
    n_docs = collection.count()

    oai = OpenAI()
    query_embedding = oai.embeddings.create(
        input=[query],
        model="text-embedding-3-small"
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_docs,
        include=["documents", "metadatas"],
    )

    return [
        {"policy_name": m["policy_name"], "text": d}
        for m, d in zip(results["metadatas"][0], results["documents"][0])
    ]
