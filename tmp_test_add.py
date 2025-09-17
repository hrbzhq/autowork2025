import chromadb
from pathlib import Path
import numpy as np
print('test add start')
persist_dir = str(Path('.').resolve() / '.chromadb')
print('persist_dir=', persist_dir)
try:
    settings = chromadb.Settings(persist_directory=persist_dir, is_persistent=True)
    client = chromadb.Client(settings=settings)
    print('client created')
except Exception as e:
    print('failed to create client with settings:', e)
    client = chromadb.Client()
    print('fallback client created')

# create or get collection
try:
    if hasattr(client, 'get_or_create_collection'):
        col = client.get_or_create_collection(name='agent_memory', metadata={"source": "autowork2025"})
    else:
        try:
            col = client.get_collection(name='agent_memory')
        except Exception:
            col = client.create_collection(name='agent_memory', metadata={"source": "autowork2025"})
    print('collection object:', type(col))
except Exception as e:
    print('failed to get/create collection:', e)
    raise

# prepare a tiny embedding
vec = [0.1] * 8
try:
    # try upsert then add
    if hasattr(col, 'upsert'):
        print('using upsert')
        col.upsert(ids=['test-1'], embeddings=[vec], metadatas=[{'lesson':'test entry'}])
    else:
        print('using add')
        col.add(ids=['test-1'], embeddings=[vec], metadatas=[{'lesson':'test entry'}])
    print('added')
except Exception as e:
    print('add/upsert failed:', e)

try:
    if hasattr(client, 'persist'):
        client.persist()
        print('client.persist() called')
except Exception as e:
    print('persist failed:', e)

# print collection count and sample
try:
    if hasattr(col, 'count'):
        print('count ->', col.count())
    res = col.get(limit=5)
    print('get keys:', list(res.keys()))
    print('ids:', res.get('ids'))
    print('metadatas:', res.get('metadatas'))
except Exception as e:
    print('query failed:', e)

print('test add end')
