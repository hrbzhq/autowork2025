import sys
from chromadb.config import Settings
import chromadb

def main(q=None, topk=5):
    # try to open persistent client first
    try:
        client = chromadb.Client(Settings(chroma_db_impl='duckdb+parquet', persist_directory='.chromadb'))
    except Exception:
        try:
            client = chromadb.Client()
        except Exception as e:
            print('Failed to initialize chromadb client:', e)
            return
    try:
        col = client.get_collection(name='agent_memory')
    except Exception:
        try:
            col = client.get_or_create_collection(name='agent_memory')
        except Exception as e:
            print('Failed to access collection agent_memory:', e)
            return

    if not q:
        # default: use a sample lesson
        try:
            meta = col.get(ids=['0'])['metadatas'][0]
            q = meta.get('lesson', '')
        except Exception:
            q = ''
    print('Query:', q)
    # naive: use text -> no encoder here, assume collection has embeddings
    try:
        # some Chroma versions support query by text; else use a simple approach
        res = col.query(query_texts=[q], n_results=topk)
    except Exception:
        try:
            # fallback: use first vector as query
            first_vec = col.get(ids=['0'])['embeddings'][0]
            res = col.query(query_embeddings=[first_vec], n_results=topk)
        except Exception as e:
            print('Query failed:', e)
            return

    ids = res.get('ids', [[]])[0]
    dists = res.get('distances', [[]])[0]
    for i, (idstr, score) in enumerate(zip(ids, dists)):
        meta = col.get(ids=[idstr])['metadatas'][0]
        print(f"{i+1}. id={idstr} score={score:.4f} lesson={meta.get('lesson')[:140]!r}")

if __name__ == '__main__':
    q = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else None
    main(q=q)
