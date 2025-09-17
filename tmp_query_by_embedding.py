from chromadb import Settings, Client
from pathlib import Path

print('tmp_query_by_embedding start')
try:
    from sentence_transformers import SentenceTransformer
except Exception as e:
    print('sentence_transformers not available:', e)
    raise

import numpy as np
persist_dir = str(Path('.').resolve()/'.chromadb')
print('persist_dir=', persist_dir)
settings = Settings(persist_directory=persist_dir, is_persistent=True)
client = Client(settings=settings)
col = client.get_collection('agent_memory')
print('col type', type(col))
# build query embedding with same model used earlier
model = SentenceTransformer('all-MiniLM-L6-v2')
q = 'Keep tasks small'
qvec = model.encode([q], show_progress_bar=False)[0].tolist()
res = col.query(query_embeddings=[qvec], n_results=5)
print('query res keys', list(res.keys()))
print('ids', res.get('ids'))
print('distances', res.get('distances'))
print('tmp_query_by_embedding end')
