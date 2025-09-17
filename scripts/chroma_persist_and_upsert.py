import time
import sys
from pathlib import Path
# ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
from memory_store import MemoryStore

def main():
    ms = MemoryStore()
    print('Loaded MemoryStore with', len(ms.lessons), 'lessons')
    # Generate full embeddings (this may download a model if not present)
    print('Generating full embeddings (may take time)...')
    ms.embed_lessons()
    print('Embeddings generated and written to agent_memory_embeddings.jsonl')
    # attempt to upsert full vectors: this uses internal _ensure_vector_index/_upsert_vectors
    try:
        # Re-load embeddings from file isn't necessary; embed_lessons already tries upsert
        print('Ensuring vector index and upserting vectors...')
        # As a safety, call embed_lessons again which triggers upsert path
        ms.embed_lessons()
        print('Upsert attempted. If Chroma is available it should be persisted under .chromadb')
    except Exception as e:
        print('Upsert failed:', e)

if __name__ == '__main__':
    main()
