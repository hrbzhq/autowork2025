import sys
from pathlib import Path
import chromadb

def main():
    persist_dir = Path(__file__).resolve().parents[1] / '.chromadb'
    persist_dir.mkdir(parents=True, exist_ok=True)
    print('Ensured persist directory:', persist_dir)
    try:
        # Use new chromadb 1.0.x Settings API to request a persistent duckdb+parquet backend
        try:
            settings = chromadb.Settings(persist_directory=str(persist_dir), is_persistent=True)
            client = chromadb.Client(settings=settings)
        except Exception:
            # fallback: try non-persistent settings or default constructor
            try:
                settings = chromadb.Settings(is_persistent=False)
                client = chromadb.Client(settings=settings)
            except Exception:
                client = chromadb.Client()
    except Exception as e:
        print('Failed to create chromadb client:', e)
        return
    try:
        # new chroma requires collection metadata to be non-empty when creating
        try:
            col = client.get_or_create_collection(name='agent_memory', metadata={"source": "autowork2025"})
        except Exception:
            col = client.create_collection(name='agent_memory', metadata={"source": "autowork2025"})
    except Exception as e:
        print('Failed to create collection:', e)
        return
    print('Chroma collection ready. You should see persistence files under', persist_dir)

if __name__ == '__main__':
    main()
