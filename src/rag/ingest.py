import os
import chromadb
import frontmatter
from pathlib import Path
from openai import OpenAI

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
POLICIES_DIR = Path(__file__).parent.parent / "data" / "policies"


def ingest() -> int:
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    try:
        client.delete_collection("policies")
    except Exception:
        pass
    collection = client.create_collection("policies")

    oai = OpenAI()
    docs, metas, ids = [], [], []

    for md_file in sorted(POLICIES_DIR.glob("*.md")):
        post = frontmatter.load(str(md_file))
        full_text = md_file.read_text(encoding="utf-8")
        policy_name = post.metadata["policy_name"]
        docs.append(full_text)
        metas.append({"policy_name": policy_name})
        ids.append(policy_name)

    embeddings = oai.embeddings.create(
        input=docs,
        model="text-embedding-3-small"
    ).data

    collection.add(
        documents=docs,
        embeddings=[e.embedding for e in embeddings],
        metadatas=metas,
        ids=ids,
    )

    print(f"✅ {len(docs)}개 정책 문서 인덱싱 완료")
    return len(docs)
