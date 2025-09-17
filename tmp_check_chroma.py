import sys
import traceback
from pathlib import Path
from datetime import datetime

print('=== tmp_check_chroma.py start ===')
print('cwd=', Path('.').resolve())
print('time=', datetime.now().isoformat())

try:
    import chromadb
    print('chromadb imported, version =', getattr(chromadb, '__version__', 'unknown'))
except Exception as e:
    print('chromadb import failed:', e)
    traceback.print_exc()
    sys.exit(2)

# try Settings path for duckdb+parquet persistent backend
try:
    from chromadb.config import Settings
    settings = Settings(chroma_db_impl='duckdb+parquet', persist_directory='.chromadb')
    print('Attempting to initialize chromadb.Client with duckdb+parquet persist_directory=.chromadb')
    client = chromadb.Client(settings)
    print('Client created with Settings')
except Exception as e:
    print('Failed to create Client with Settings (duckdb+parquet):', e)
    traceback.print_exc()
    try:
        print('Attempting default chromadb.Client() fallback')
        client = chromadb.Client()
    except Exception as e2:
        print('Fallback Client() failed:', e2)
        traceback.print_exc()
        sys.exit(3)

# access or create collection
try:
    try:
        col = client.get_collection(name='agent_memory')
        print('Got collection agent_memory via get_collection')
    except Exception:
        col = client.get_or_create_collection(name='agent_memory')
        print('Created or got collection agent_memory via get_or_create_collection')

    # attempt to get a count/preview
    count = None
    try:
        count = col.count()
        print('Collection.count() ->', count)
    except Exception:
        try:
            res = col.get()
            ids = res.get('ids', [])
            # ids maybe list of lists depending on API
            if isinstance(ids, list) and ids and isinstance(ids[0], list):
                count = len(ids[0])
            else:
                count = len(ids)
            print('Collection.get() ids length ->', count)
        except Exception as e:
            print('Could not determine collection size:', e)
            traceback.print_exc()
            count = 'unknown'

    # try to print first metadata
    try:
        sample = None
        # try common get patterns
        res = col.get(ids=['0'])
        metas = res.get('metadatas', [])
        if metas and isinstance(metas, list):
            sample = metas[0]
        else:
            # fallback: get first returned id from get()
            res2 = col.get()
            ids2 = res2.get('ids', [])
            first_id = None
            if isinstance(ids2, list) and ids2:
                first = ids2[0]
                if isinstance(first, list) and first:
                    first_id = first[0]
                else:
                    first_id = first
            if first_id is not None:
                res3 = col.get(ids=[first_id])
                sample = res3.get('metadatas', [None])[0]
        print('Sample metadata for id 0 or first id ->', sample)
    except Exception as e:
        print('Could not fetch sample metadata:', e)
        traceback.print_exc()

except Exception as e:
    print('Error working with collection:', e)
    traceback.print_exc()

print('=== tmp_check_chroma.py end ===')
