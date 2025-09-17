import json
from chromadb.config import Settings
import chromadb
import numpy as np
import sys

EMBED_FILE = 'agent_memory_embeddings.jsonl'

def load_embeddings(path):
    items = []
    with open(path, 'r', encoding='utf-8') as f:
        for ln in f:
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            items.append(obj)
    return items

def main():
    items = load_embeddings(EMBED_FILE)
    if not items:
        print('No embeddings found in', EMBED_FILE)
        sys.exit(1)

    # Try multiple ways to construct a Chroma client to handle API differences
    client = None
    try:
        client = chromadb.Client(Settings(chroma_db_impl=':memory:'))
    except Exception:
        try:
            client = chromadb.Client()
        except Exception:
            print('Failed to initialize chromadb client. Your chromadb version may require migration.')
            print('Try: pip install chromadb==0.3.26 or follow migration docs: https://docs.trychroma.com/deployment/migration')
            return

    try:
        col = client.create_collection(name='agent_memory_demo')
    except Exception:
        # newer versions may require a different call signature
        try:
            col = client.get_or_create_collection(name='agent_memory_demo')
        except Exception as e:
            print('Failed to create or get collection:', e)
            return

    ids = [str(it['id']) for it in items]
    metadatas = [{'lesson': it.get('lesson')} for it in items]
    # Use vec_summary (first 8 dims) as lightweight vector for demo
    vecs = [it.get('vec_summary') or [0.0]*8 for it in items]

    col.add(ids=ids, metadatas=metadatas, embeddings=vecs)

    # Run a sample query: use first lesson text as a query
    query_text = items[0].get('lesson', '')
    print('Querying with:', query_text)
    # produce a query embedding using the same lightweight vec (here we reuse vec_summary of first)
    qvec = vecs[0]
    res = col.query(query_embeddings=[qvec], n_results=5)
    print('Top results:')
    ids_out = res.get('ids', [[]])[0]
    dists = res.get('distances', [[]])[0]
    for i, (idstr, score) in enumerate(zip(ids_out, dists)):
        meta = col.get(ids=[idstr])['metadatas'][0]
        print(f"{i+1}. id={idstr} score={score:.4f} lesson={meta.get('lesson')[:120]!r}")

if __name__ == '__main__':
    main()
