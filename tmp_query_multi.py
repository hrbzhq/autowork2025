from pathlib import Path
import traceback
import json

q = 'Keep tasks small'
print('Query:', q)

try:
    import chromadb
    from chromadb import Settings, Client
except Exception as e:
    print('chromadb import failed:', e)
    raise

persist_dir = str(Path('.').resolve() / '.chromadb')
print('Using persist_dir=', persist_dir)
try:
    settings = Settings(persist_directory=persist_dir, is_persistent=True)
    client = Client(settings=settings)
    print('Created persistent client')
except Exception as e:
    print('Settings client failed:', e)
    client = Client()
    print('Created default client')

# get collection
try:
    col = client.get_collection('agent_memory')
    print('Got collection object')
except Exception as e:
    print('get_collection failed:', e)
    raise

# Strategy 1: try query by text
try:
    print('\nTrying col.query(query_texts=...)')
    res = col.query(query_texts=[q], n_results=5)
    print('res keys:', list(res.keys()))
    ids = res.get('ids', [[]])[0]
    dists = res.get('distances', [[]])[0]
    if ids:
        print('Results (text query):')
        for i,(id_,d) in enumerate(zip(ids,dists),1):
            try:
                meta = col.get(ids=[id_]).get('metadatas',[None])[0]
            except Exception:
                meta = None
            print(f'{i}. id={id_} score={d} meta={meta}')
    else:
        print('col.query(query_texts=...) returned no ids')
except Exception as e:
    print('text query failed:', e)
    traceback.print_exc()

# Strategy 2: try to compute embedding with transformers / sentence-transformers
qvec = None
try:
    print('\nAttempting to compute query embedding via sentence-transformers or transformers fallback')
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        qvec = model.encode([q], show_progress_bar=False)[0].tolist()
        print('Used sentence-transformers')
    except Exception as e:
        print('sentence-transformers unavailable:', e)
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch
            tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
            model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
            model.eval()
            with torch.no_grad():
                inputs = tokenizer(q, return_tensors='pt', truncation=True, padding=True)
                out = model(**inputs)
                last = out.last_hidden_state[0]
                vec = last.mean(dim=0).cpu().numpy()
                qvec = vec.tolist()
                print('Used transformers fallback')
        except Exception as e2:
            print('transformers fallback failed:', e2)
except Exception:
    traceback.print_exc()

# Strategy 3: fallback deterministic pseudo-embedding
if qvec is None:
    print('\nUsing deterministic pseudo-embedding fallback')
    import numpy as np
    buf = (q[:256].ljust(256)).encode('utf-8')
    arr = np.frombuffer(buf, dtype='u1').astype(float)
    qvec = arr.tolist()

# Strategy 4: try col.query with embeddings
try:
    print('\nTrying col.query(query_embeddings=...)')
    res = col.query(query_embeddings=[qvec], n_results=5)
    print('res keys:', list(res.keys()))
    ids = res.get('ids', [[]])[0]
    dists = res.get('distances', [[]])[0]
    if ids:
        print('Results (embedding query):')
        for i,(id_,d) in enumerate(zip(ids,dists),1):
            try:
                meta = col.get(ids=[id_]).get('metadatas',[None])[0]
            except Exception:
                meta = None
            print(f'{i}. id={id_} score={d} meta={meta}')
    else:
        print('col.query(query_embeddings=...) returned no ids')
except Exception as e:
    print('embedding query failed:', e)
    traceback.print_exc()

# Final fallback: use local agent_memory_embeddings.jsonl vec_summary
try:
    print('\nFallback: use local agent_memory_embeddings.jsonl vec_summary cosine sim')
    fn = Path(__file__).with_name('agent_memory_embeddings.jsonl')
    if fn.exists():
        import numpy as np
        items = []
        with open(fn,'r',encoding='utf-8') as f:
            for ln in f:
                try:
                    obj = json.loads(ln)
                except Exception:
                    continue
                items.append(obj)
        if items:
            mat = np.array([(it.get('vec_summary') or []) + [0.0]*8 for it in items], dtype=float)[:,:8]
            # compute small query vec
            qsmall = (qvec[:8] + [0.0]*8)[:8]
            qsmall = np.array(qsmall, dtype=float)
            sims = (mat @ qsmall) / (np.linalg.norm(mat, axis=1) * (np.linalg.norm(qsmall) + 1e-12))
            idxs = sims.argsort()[::-1][:5]
            print('Local vec_summary top results:')
            for rank,i in enumerate(idxs,1):
                print(f'{rank}. idx={int(i)} score={float(sims[int(i)])} lesson={items[int(i)].get("lesson")[:140]!r}')
        else:
            print('No items in agent_memory_embeddings.jsonl')
    else:
        print('agent_memory_embeddings.jsonl not found')
except Exception as e:
    print('fallback local sim failed:', e)
    traceback.print_exc()

print('\nDone')
