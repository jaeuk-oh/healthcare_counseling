"""정책 문서를 ChromaDB에 인덱싱하는 초기화 스크립트."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from src.rag.ingest import ingest

if __name__ == "__main__":
    count = ingest()
    print(f"인덱싱 완료: {count}개 문서")
