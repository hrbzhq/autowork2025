#!/usr/bin/env python3
"""
Embed agent_memory.txt using SentenceTransformer (local).

Outputs:
 - agent_memory_embeddings.jsonl  (one object per lesson: {id, lesson, vec_len, vec_summary})

Run: python d:\study\embed_memory.py
"""
import os
import json
import sys
from pathlib import Path

TXT = Path(__file__).with_name('agent_memory.txt')
OUT_JSONL = Path(__file__).with_name('agent_memory_embeddings.jsonl')


def load_lessons(path):
    if not path.exists():
        print('No agent_memory.txt found at', path)
        return []
    with open(path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines


def try_sentence_transformers():
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except Exception as e:
        print('SentenceTransformer unavailable:', e)
        return None


def try_transformers_fallback():
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch

        class TFEncoder:
            def __init__(self, name='sentence-transformers/all-MiniLM-L6-v2'):
                self.tokenizer = AutoTokenizer.from_pretrained(name)
                self.model = AutoModel.from_pretrained(name)
                self.model.eval()

            def encode(self, texts, show_progress_bar=False):
                import numpy as np
                vectors = []
                with torch.no_grad():
                    for t in texts:
                        inputs = self.tokenizer(t, return_tensors='pt', truncation=True, padding=True)
                        out = self.model(**inputs)
                        # mean pooling of last_hidden_state
                        last = out.last_hidden_state[0]
                        vec = last.mean(dim=0).cpu().numpy()
                        vectors.append(vec)
                return np.stack(vectors)

        return TFEncoder()
    except Exception as e:
        print('Transformers fallback unavailable:', e)
        return None


def encode_with_model(model, texts):
    vecs = model.encode(texts, show_progress_bar=False)
    return vecs


def simple_sim(vecs, qvec, topk=5):
    import numpy as np
    sims = (vecs @ qvec) / (np.linalg.norm(vecs, axis=1) * (np.linalg.norm(qvec) + 1e-12))
    idx = sims.argsort()[::-1][:topk]
    return idx, sims[idx]


def main():
    lessons = load_lessons(TXT)
    if not lessons:
        return

    model = try_sentence_transformers()
    real_model = False
    fallback_encoder = None
    if model is None:
        # try transformers-based fallback
        fallback_encoder = try_transformers_fallback()
        if fallback_encoder is not None:
            print('Using transformers-based fallback encoder (AutoModel mean pooling).')
            model = fallback_encoder
            real_model = True
        else:
            print('Falling back to simulated embeddings (not recommended for production).')

    import numpy as np
    if model is None:
        # deterministic pseudo-embeddings
        vecs = np.stack([np.frombuffer((l[:64].ljust(64)).encode('utf-8'), dtype='u1').astype(float) for l in lessons])
    else:
        vecs = encode_with_model(model, lessons)
        real_model = True

    # write JSONL with small vector summary (length, first 8 dims)
    with open(OUT_JSONL, 'w', encoding='utf-8') as f:
        for i, l in enumerate(lessons):
            v = vecs[i]
            summary = None
            try:
                summary = [float(x) for x in list(v[:8])]
            except Exception:
                summary = []
            obj = {
                'id': i,
                'lesson': l,
                'vec_len': int(len(v)) if hasattr(v, '__len__') else None,
                'vec_summary': summary,
            }
            json.dump(obj, f, ensure_ascii=False)
            f.write('\n')

    print(f'Wrote embeddings JSONL: {OUT_JSONL} (lessons={len(lessons)})')

    # demo: nearest neighbors for a sample query
    demo_q = 'verify json format'
    print('\nDemo similarity query:', demo_q)
    if not real_model:
        print('No real model available; skipping similarity demo.')
        return
    qvec = model.encode([demo_q])[0]
    import numpy as np
    idxs, scores = simple_sim(np.array(vecs), qvec, topk=5)
    for rank, (i, s) in enumerate(zip(idxs, scores), start=1):
        print(f"{rank}. (score={float(s):.4f}) {lessons[int(i)]}")


if __name__ == '__main__':
    main()
