import chromadb
from chromadb.config import Settings
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch

# init persistent client
settings = chromadb.Settings(persist_directory='.chromadb', is_persistent=True)
client = chromadb.Client(settings=settings)
col = client.get_collection(name='agent_memory')

q = "Keep tasks small and test frequently"
# generate embedding via transformers mean-pool
tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
model.eval()
with torch.no_grad():
    inputs = tokenizer(q, return_tensors='pt', truncation=True, padding=True)
    out = model(**inputs)
    last = out.last_hidden_state[0]
    vec = last.mean(dim=0).cpu().numpy().tolist()

res = col.query(query_embeddings=[vec], n_results=5)
print('query result keys:', res.keys())
ids = res.get('ids', [[]])[0]
dists = res.get('distances', [[]])[0]
print('ids:', ids)
print('dists:', dists)
for idstr, score in zip(ids, dists):
    m = col.get(ids=[idstr])['metadatas'][0]
    print('id', idstr, 'score', score, 'lesson', m.get('lesson')[:200])
