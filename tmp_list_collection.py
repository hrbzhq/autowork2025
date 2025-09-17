import chromadb
from pathlib import Path
import json

print('=== list collection diagnostic ===')
print('cwd=', Path('.').resolve())
print('chromadb version =', getattr(chromadb, '__version__', 'unknown'))

# try persistent settings
try:
    settings = chromadb.Settings(persist_directory=str(Path('.').resolve() / '.chromadb'), is_persistent=True)
    client = chromadb.Client(settings=settings)
    print('Client created with Settings(persist_directory, is_persistent=True)')
except Exception as e:
    print('Settings client failed:', e)
    try:
        client = chromadb.Client()
        print('Client created with default constructor')
    except Exception as e2:
        print('Default client failed too:', e2)
        raise

# list collections
try:
    cols = client.list_collections()
    print('Collections:', [c['name'] for c in cols])
except Exception as e:
    print('list_collections failed:', e)

# access agent_memory
try:
    if hasattr(client, 'get_collection'):
        col = client.get_collection('agent_memory')
    else:
        col = client.get_or_create_collection('agent_memory')
    print('Got collection object:', type(col))
    # try count
    try:
        cnt = col.count()
        print('col.count() ->', cnt)
    except Exception as e:
        print('col.count() failed:', e)
    # try get first 5
    try:
        res = col.get(limit=5)
        print('col.get(limit=5) keys:', list(res.keys()))
        ids = res.get('ids', [])
        metas = res.get('metadatas', [])
        emb = res.get('embeddings', None)
        print('ids (raw):', ids)
        print('metas (raw):', metas[:5])
        print('embeddings present?', emb is not None)
    except Exception as e:
        print('col.get failed:', e)
    # try get by ids if available
    try:
        if ids:
            # normalize ids list
            first_ids = ids[0] if isinstance(ids[0], list) else ids
            sample_ids = first_ids[:3]
            print('trying col.get(ids=sample_ids):', sample_ids)
            res2 = col.get(ids=[str(x) for x in sample_ids])
            print('res2 keys:', list(res2.keys()))
            print('res2 metadatas:', res2.get('metadatas'))
            print('res2 embeddings present?', 'embeddings' in res2 and res2['embeddings'])
    except Exception as e:
        print('col.get(ids=...) failed:', e)
except Exception as e:
    print('Could not access agent_memory collection:', e)

print('=== end ===')
