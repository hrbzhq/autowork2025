import os
import json
import re
from pathlib import Path
from typing import List, Optional, Tuple
import threading
import time

# Optional vector DB backends: try to import chroma and faiss, set flags
HAS_CHROMA = False
HAS_FAISS = False
try:
    import chromadb  # type: ignore
    HAS_CHROMA = True
except Exception:
    HAS_CHROMA = False
try:
    import faiss  # type: ignore
    HAS_FAISS = True
except Exception:
    HAS_FAISS = False

MEMORY_FILE = Path(__file__).with_name('agent_memory.txt')
EMBED_JSONL = Path(__file__).with_name('agent_memory_embeddings.jsonl')

# Background worker config
EMBED_BATCH_INTERVAL = 2.0  # seconds to wait between batch embeds when work is queued
EMBED_BATCH_SIZE = 64


class MemoryStore:
    """A small local-first memory store for concise lessons.

    Features:
    - file-backed lessons (one per line)
    - sanitization and aggressive sanitization methods
    - add_lesson / get_context API compatible with previous SimpleMemory
    - embed_lessons triggers the embed script (or uses an inline fallback encoder)
    - find_similar returns top-k indices using available embeddings (or empty if none)
    """

    def __init__(self, path: Optional[str] = None):
        self.path = MEMORY_FILE if path is None else Path(path)
        self.lessons: List[str] = []
        self._embed_lock = threading.Lock()
        self._embed_queue: List[int] = []  # indices of lessons needing embedding refresh
        self._worker: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
        # vector DB components (lazy)
        self._vector_index = None
        self._vec_dim = None
        self._sanitize_file()
        self._load()
        # start background worker lazily
        self._ensure_worker_started()

    def _sanitize_file(self):
        if not self.path.exists():
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
            cleaned = []
            seen = set()
            for ln in lines:
                ln_clean = ln
                try:
                    parsed = json.loads(ln)
                    candidate = None
                    if isinstance(parsed, str):
                        candidate = parsed
                    elif isinstance(parsed, list) and parsed:
                        for el in parsed:
                            if isinstance(el, str) and el.strip():
                                candidate = el.strip()
                                break
                    elif isinstance(parsed, dict):
                        for k in ("lesson", "response", "result", "message", "text"):
                            if k in parsed and isinstance(parsed[k], str) and parsed[k].strip():
                                candidate = parsed[k].strip()
                                break
                        if not candidate:
                            for v in parsed.values():
                                if isinstance(v, str) and v.strip():
                                    candidate = v.strip()
                                    break
                    if candidate:
                        ln_clean = candidate
                    else:
                        ln_clean = re.sub(r"<\/?think>|thinking|done thinking|SUCCESS:|Result:", "", ln, flags=re.IGNORECASE).strip()
                except Exception:
                    ln_clean = re.sub(r"<\/?think>|thinking|done thinking|SUCCESS:|Result:", "", ln, flags=re.IGNORECASE).strip()
                ln_clean = re.sub(r"\s+", " ", ln_clean).strip()
                if not ln_clean or len(ln_clean) < 10:
                    continue
                if ln_clean in seen:
                    continue
                seen.add(ln_clean)
                cleaned.append(ln_clean)
            with open(self.path, 'w', encoding='utf-8') as f:
                for ln in cleaned:
                    f.write(ln + "\n")
        except Exception:
            return

    def aggressive_sanitize_file(self):
        if not self.path.exists():
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
            cleaned = []
            seen = set()
            for ln in lines:
                candidate = None
                try:
                    parsed = json.loads(ln)
                    if isinstance(parsed, str):
                        candidate = parsed
                    elif isinstance(parsed, list) and parsed:
                        for el in parsed:
                            if isinstance(el, str) and el.strip():
                                candidate = el.strip()
                                break
                    elif isinstance(parsed, dict):
                        for k in ("lesson", "response", "result", "message", "text"):
                            if k in parsed and isinstance(parsed[k], str) and parsed[k].strip():
                                candidate = parsed[k].strip()
                                break
                        if not candidate:
                            for v in parsed.values():
                                if isinstance(v, str) and v.strip():
                                    candidate = v.strip()
                                    break
                except Exception:
                    candidate = None
                if not candidate:
                    s2 = re.sub(r"```[\s\S]*?```", "", ln)
                    s2 = re.sub(r"<\/?think>|\bthought:\b|let's think|let me think|step by step|chain-of-thought", "", s2, flags=re.IGNORECASE)
                    s2 = re.sub(r"\{\s*'|\"|\}\s*|\[|\]", "", s2)
                    s2 = re.sub(r"SUCCESS:|Result:|Response:", "", s2, flags=re.IGNORECASE)
                    s2 = re.sub(r"\s+", " ", s2).strip()
                    first = re.split(r'[\.\!\?\n]', s2)[0].strip()
                    candidate = first
                if not candidate:
                    continue
                candidate = re.sub(r"\s+", " ", candidate).strip()
                if len(candidate) < 12:
                    continue
                if candidate in seen:
                    continue
                seen.add(candidate)
                cleaned.append(candidate)
            with open(self.path, 'w', encoding='utf-8') as f:
                for ln in cleaned:
                    f.write(ln + "\n")
            self.lessons = cleaned
        except Exception:
            return

    def _load(self):
        if not self.path.exists():
            self.lessons = []
            return
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                items = [l.strip() for l in f if l.strip()]
            seen = set()
            deduped = []
            for it in items:
                if it in seen:
                    continue
                seen.add(it)
                deduped.append(it)
            self.lessons = deduped
        except Exception:
            self.lessons = []

    def add_lesson(self, lesson: str):
        raw = lesson
        lesson = lesson.strip()
        try:
            parsed = json.loads(lesson)
            if isinstance(parsed, str):
                lesson = parsed
            elif isinstance(parsed, dict):
                for k in ("lesson", "response", "result", "message", "text"):
                    if k in parsed and isinstance(parsed[k], str) and parsed[k].strip():
                        lesson = parsed[k].strip()
                        break
                else:
                    for v in parsed.values():
                        if isinstance(v, str) and v.strip():
                            lesson = v.strip()
                            break
            elif isinstance(parsed, list) and parsed:
                for el in parsed:
                    if isinstance(el, str) and el.strip():
                        lesson = el.strip()
                        break
        except Exception:
            lesson = lesson
        lesson = re.sub(r"\s+", " ", lesson)
        if not lesson or len(lesson) < 10:
            return
        # reject obvious chain-of-thought/noise patterns and artifact dumps
        if re.search(r"<\/?think>|\[think\]|\(thinking\)|okay,? let(?:'s)? see|i need to think|thinking\.\.\.", lesson, flags=re.IGNORECASE):
            return
        # reject lines that look like dumped objects / logs (contain unnatural tokens)
        if re.search(r"Response':|Thread_id|user_id|Lesson':|Lesson\:|Lesson\'|Lesson\"|\bResponse\:|\bResult\:|\{\s*'|\[\s*'", lesson, flags=re.IGNORECASE):
            return
        # reject lines with many unmatched quotes or punctuation suggesting a dump
        if lesson.count("'") > 6 or lesson.count('"') > 6:
            return
        if len(lesson) > 200:
            lesson = lesson[:197].rsplit(' ', 1)[0] + '...'
        if lesson in self.lessons:
            return
        for existing in self.lessons[-10:]:
            if lesson in existing or existing in lesson:
                return
        try:
            print(f"[Memory] Adding lesson: {lesson}")
        except Exception:
            pass
        self.lessons.append(lesson)
        try:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.write(lesson.replace('\n', ' ') + '\n')
        except Exception:
            pass

    def sanitize_existing(self):
        """Run aggressive sanitization and a final pass to remove artifact-like lines.

        This is intended to be called at mission end to clean up noisy historic entries.
        """
        # aggressive pass rewrites the file and populates self.lessons
        try:
            self.aggressive_sanitize_file()
        except Exception:
            pass
        # load current lines and perform one more filter pass
        try:
            if not self.path.exists():
                return
            with open(self.path, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f if l.strip()]
            cleaned = []
            seen = set()
            for ln in lines:
                # remove obvious artifacts
                if re.search(r"Response':|Thread_id|user_id|Lesson':|Lesson\:|Lesson\'|Lesson\"|\bResponse\:|\bResult\:", ln, flags=re.IGNORECASE):
                    continue
                if ln.count("'") > 6 or ln.count('"') > 6:
                    continue
                # remove incomplete fragments ending with '...'
                if ln.strip().endswith('...') and len(ln) < 40:
                    continue
                s = re.sub(r"\s+", " ", ln).strip()
                if len(s) < 10:
                    continue
                if s in seen:
                    continue
                seen.add(s)
                cleaned.append(s)
            # overwrite file with cleaned lessons
            with open(self.path, 'w', encoding='utf-8') as f:
                for c in cleaned:
                    f.write(c + '\n')
            # reload into memory
            self.lessons = cleaned
        except Exception:
            return

    def get_context(self) -> str:
        if not self.lessons:
            return "No past experiences or lessons learned yet."
        return "--- Past Lessons Learned ---\n" + "\n".join(f"- {l}" for l in self.lessons)

    # Embedding helpers: a thin wrapper that imports sentence-transformers or fallback
    def _ensure_worker_started(self):
        if self._worker and self._worker.is_alive():
            return
        self._stop_worker.clear()
        self._worker = threading.Thread(target=self._embed_worker, daemon=True)
        self._worker.start()

    def stop_worker(self, timeout: float = 1.0):
        self._stop_worker.set()
        if self._worker:
            self._worker.join(timeout=timeout)

    def _embed_worker(self):
        """Background thread to process embed queue in batches."""
        while not self._stop_worker.is_set():
            try:
                if not self._embed_queue:
                    # sleep briefly and recheck
                    time.sleep(0.2)
                    continue
                # gather indices to process
                with self._embed_lock:
                    idxs = list(set(self._embed_queue))
                    self._embed_queue.clear()
                if not idxs:
                    continue
                # For now we regenerate all embeddings for simplicity (cheap for small memory)
                try:
                    self.embed_lessons()
                except Exception:
                    pass
                # throttle between batches
                time.sleep(EMBED_BATCH_INTERVAL)
            except Exception:
                time.sleep(0.5)

    def embed_lessons(self) -> None:
        """Produce embeddings JSONL for current lessons using existing embed script logic.

        This method is intentionally minimal: it will try to import sentence-transformers and
        fallback to transformers mean-pool. If neither is available it will write deterministic
        pseudo-embeddings.
        """
        # Prefer sentence-transformers; fallback to transformers mean-pooling.
        # We intentionally prefer transformers fallback here to ensure we can produce
        # full 384-dimension vectors even if sentence-transformers fails to import
        # (common due to huggingface_hub version mismatches). If both fail we use
        # deterministic pseudo-vectors.
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            vecs = model.encode(self.lessons, show_progress_bar=False)
            real = True
        except Exception:
            try:
                # transformers fallback (mean pooling) -- more robust in constrained envs
                from transformers import AutoTokenizer, AutoModel
                import torch
                tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model.eval()
                import numpy as np
                vecs = []
                with torch.no_grad():
                    for t in self.lessons:
                        inputs = tokenizer(t, return_tensors='pt', truncation=True, padding=True)
                        out = model(**inputs)
                        last = out.last_hidden_state[0]
                        vec = last.mean(dim=0).cpu().numpy()
                        vecs.append(vec)
                vecs = np.stack(vecs)
                real = True
            except Exception:
                # deterministic pseudo-embeddings (stable fallback)
                import numpy as np
                vecs = np.stack([np.frombuffer((l[:64].ljust(64)).encode('utf-8'), dtype='u1').astype(float) for l in self.lessons])
                real = False

        # write EMBED_JSONL with small vector summary
        try:
            with open(EMBED_JSONL, 'w', encoding='utf-8') as f:
                for i, l in enumerate(self.lessons):
                    v = vecs[i]
                    try:
                        summary = [float(x) for x in list(v[:8])]
                    except Exception:
                        summary = []
                    obj = {'id': i, 'lesson': l, 'vec_len': int(len(v)) if hasattr(v, '__len__') else None, 'vec_summary': summary}
                    json.dump(obj, f, ensure_ascii=False)
                    f.write('\n')
        except Exception:
            pass

        # also upsert into optional vector DB (best-effort)
        try:
            self._ensure_vector_index(vecs)
            self._upsert_vectors(vecs)
        except Exception:
            # ignore vector DB failures (keep embeddings JSONL as primary artifact)
            pass

    def find_similar(self, query: str, topk: int = 3) -> List[Tuple[int, float]]:
        """Return list of (index, score) for top-k similar lessons using summaries if available.

        This is intentionally lightweight: it will try to load EMBED_JSONL and compute cosine
        similarity with a query embedding produced by the same local encoder. If embeddings are
        unavailable it returns an empty list.
        """
        # If we have a vector DB, use it first
        try:
            if self._vector_index is not None:
                return self._query_vector_db(query, topk)
        except Exception:
            pass

        # quick path: if no embeddings file, return empty
        if not EMBED_JSONL.exists():
            return []
        # load summaries and attempt to reconstruct a small matrix
        import numpy as np
        items = []
        try:
            with open(EMBED_JSONL, 'r', encoding='utf-8') as f:
                for ln in f:
                    if not ln.strip():
                        continue
                    try:
                        obj = json.loads(ln)
                    except Exception:
                        continue
                    items.append(obj)
        except Exception:
            return []
        if not items:
            return []
        # If real full vectors aren't available, use vec_summary padded
        mat = []
        for it in items:
            s = it.get('vec_summary') or []
            # pad/truncate to 8 dims
            row = (s + [0.0] * 8)[:8]
            mat.append(row)
        mat = np.array(mat, dtype=float)

        # produce query vec using same small encoder (best-effort)
        qvec = None
        try:
            # try sentence-transformers or transformers fallback quickly
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                qvec_full = model.encode([query], show_progress_bar=False)[0]
                qvec = np.array(list(qvec_full[:8]), dtype=float)
            except Exception:
                from transformers import AutoTokenizer, AutoModel
                import torch
                tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model.eval()
                with torch.no_grad():
                    inputs = tokenizer(query, return_tensors='pt', truncation=True, padding=True)
                    out = model(**inputs)
                    last = out.last_hidden_state[0]
                    vec = last.mean(dim=0).cpu().numpy()
                    qvec = np.array(list(vec[:8]), dtype=float)
        except Exception:
            # fallback: simple character-level vector
            qvec = np.frombuffer((query[:64].ljust(64)).encode('utf-8'), dtype='u1').astype(float)[:8]

        # cosine sim
        try:
            sims = (mat @ qvec) / (np.linalg.norm(mat, axis=1) * (np.linalg.norm(qvec) + 1e-12))
            idxs = sims.argsort()[::-1][:topk]
            return [(int(i), float(sims[int(i)])) for i in idxs]
        except Exception:
            return []

    # ----------------------
    # Vector DB support (Chroma / FAISS / In-memory fallback)
    # ----------------------
    def _ensure_vector_index(self, vecs):
        """Initialize vector index backend lazily. Accepts full vectors (numpy array or list)."""
        import numpy as np
        arr = np.array(vecs)
        if arr.size == 0:
            return
        dim = arr.shape[1]
        self._vec_dim = dim
        if HAS_CHROMA and self._vector_index is None:
            try:
                # prefer a persistent Chroma directory under the repo
                from chromadb.config import Settings
                import chromadb
                persist_dir = str(Path(__file__).with_name('.chromadb'))
                # create directory if not exists to support persistent backends
                try:
                    Path(persist_dir).mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass
                # Try to create a persistent client; fallback to in-memory if API differs
                try:
                    # chromadb 1.0+ expects Settings with persist_directory and is_persistent
                    try:
                        settings = chromadb.Settings(persist_directory=persist_dir, is_persistent=True)
                        client = chromadb.Client(settings=settings)
                    except Exception:
                        # fallback to non-persistent settings
                        try:
                            settings = chromadb.Settings(is_persistent=False)
                            client = chromadb.Client(settings=settings)
                        except Exception:
                            client = chromadb.Client()
                except Exception:
                    client = chromadb.Client()
                # create or get collection depending on API
                # New API provides get_collection/create_collection/get_or_create_collection
                try:
                    # prefer get_or_create_collection if available
                    if hasattr(client, 'get_or_create_collection'):
                        col = client.get_or_create_collection(name="agent_memory", metadata={"source": "autowork2025"})
                    else:
                        try:
                            col = client.get_collection(name="agent_memory")
                        except Exception:
                            col = client.create_collection(name="agent_memory", metadata={"source": "autowork2025"})
                except Exception:
                    # last-resort: try to create collection without metadata
                    try:
                        col = client.create_collection(name="agent_memory", metadata={"source": "autowork2025"})
                    except Exception:
                        col = None
                self._vector_index = ('chroma', client, col, persist_dir)
                return
            except Exception:
                self._vector_index = None
        if HAS_FAISS and self._vector_index is None:
            try:
                import faiss
                index = faiss.IndexFlatIP(dim)
                self._vector_index = ('faiss', index, [])  # store ids list
                return
            except Exception:
                self._vector_index = None
        # fallback: in-memory numpy store
        if self._vector_index is None:
            self._vector_index = ('memory', [], None)  # list of (id, vec)

    def _upsert_vectors(self, vecs):
        """Upsert full vectors into the selected backend. vecs is an iterable aligned with self.lessons."""
        import numpy as np
        arr = np.array(vecs)
        if arr.size == 0:
            return
        # ensure index initialized
        self._ensure_vector_index(vecs)
        kind = self._vector_index[0]
        if kind == 'chroma':
            try:
                # get client/col/persist_dir from previously created vector_index if present
                if len(self._vector_index) >= 4:
                    _, client, col, persist_dir = self._vector_index
                else:
                    _, client, col = self._vector_index
                    persist_dir = None

                ids = [str(i) for i in range(len(self.lessons))]
                metadatas = [{'lesson': self.lessons[i]} for i in range(len(self.lessons))]

                # create an explicit persistent client (pointing to persist_dir) to avoid tenant/db mismatches
                try:
                    settings = chromadb.Settings(persist_directory=persist_dir, is_persistent=True)
                    pclient = chromadb.Client(settings=settings)
                except Exception:
                    pclient = client if client is not None else chromadb.Client()

                # get or create collection on the persistent client
                try:
                    if hasattr(pclient, 'get_or_create_collection'):
                        pcol = pclient.get_or_create_collection(name='agent_memory', metadata={"source": "autowork2025"})
                    else:
                        try:
                            pcol = pclient.get_collection(name='agent_memory')
                        except Exception:
                            pcol = pclient.create_collection(name='agent_memory', metadata={"source": "autowork2025"})
                except Exception:
                    pcol = col

                # If the collection exists, try to detect an embedding-dimension mismatch.
                try:
                    need_recreate = False
                    # some Chroma versions expose 'get' returning embeddings; try to inspect one
                    if pcol is not None:
                        try:
                            sample = pcol.get(limit=1)
                            emb = sample.get('embeddings', [[]])[0]
                            if emb:
                                existing_dim = len(emb)
                                new_dim = int(arr.shape[1])
                                if existing_dim != new_dim:
                                    need_recreate = True
                        except Exception:
                            # if we cannot introspect embeddings, skip
                            need_recreate = False
                    if need_recreate:
                        try:
                            # delete and recreate collection so dim is reset for new vectors
                            if hasattr(pclient, 'delete_collection'):
                                try:
                                    pclient.delete_collection(name='agent_memory')
                                except Exception:
                                    pass
                            pcol = pclient.create_collection(name='agent_memory', metadata={"source": "autowork2025"})
                        except Exception:
                            # fallback: ignore recreate
                            pass
                except Exception:
                    pass

                # upsert or add
                try:
                    if hasattr(pcol, 'upsert'):
                        pcol.upsert(ids=ids, embeddings=arr.tolist(), metadatas=metadatas)
                    else:
                        pcol.add(ids=ids, embeddings=arr.tolist(), metadatas=metadatas)
                except Exception:
                    try:
                        if hasattr(pclient, 'delete_collection'):
                            pclient.delete_collection(name='agent_memory')
                        pcol = pclient.create_collection(name='agent_memory', metadata={})
                        pcol.add(ids=ids, embeddings=arr.tolist(), metadatas=metadatas)
                    except Exception:
                        pass

                # persist if available
                try:
                    if hasattr(pclient, 'persist'):
                        pclient.persist()
                except Exception:
                    try:
                        if persist_dir:
                            Path(persist_dir, '.persisted').write_text('persisted')
                    except Exception:
                        pass

                # quick verification
                try:
                    cnt = None
                    if hasattr(pcol, 'count'):
                        cnt = pcol.count()
                    else:
                        cres = pcol.get(limit=1)
                        ids_res = cres.get('ids', [])
                        if isinstance(ids_res, list) and ids_res and isinstance(ids_res[0], list):
                            cnt = len(ids_res[0])
                        else:
                            cnt = len(ids_res)
                    try:
                        print(f"[MemoryStore] Chroma upsert verification: collection count={cnt}")
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                pass
        elif kind == 'faiss':
            try:
                _, index, id_list = self._vector_index
                # replace index by rebuilding (simple approach)
                import faiss
                dim = arr.shape[1]
                new_index = faiss.IndexFlatIP(dim)
                new_index.add(arr.astype('float32'))
                self._vector_index = ('faiss', new_index, list(range(len(self.lessons))))
            except Exception:
                pass
        else:
            # memory fallback: store list of vectors
            try:
                self._vector_index = ('memory', [(i, arr[i]) for i in range(len(self.lessons))], None)
            except Exception:
                pass

    def _query_vector_db(self, query: str, topk: int = 3) -> List[Tuple[int, float]]:
        """Query the backend vector DB and return list of (index, score)."""
        import numpy as np
        # produce query vector using same small encoder (best-effort)
        qvec = None
        try:
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer('all-MiniLM-L6-v2')
                qvec_full = model.encode([query], show_progress_bar=False)[0]
                qvec = np.array(list(qvec_full[:self._vec_dim]), dtype=float)
            except Exception:
                from transformers import AutoTokenizer, AutoModel
                import torch
                tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
                model.eval()
                with torch.no_grad():
                    inputs = tokenizer(query, return_tensors='pt', truncation=True, padding=True)
                    out = model(**inputs)
                    last = out.last_hidden_state[0]
                    vec = last.mean(dim=0).cpu().numpy()
                    qvec = np.array(list(vec[:self._vec_dim]), dtype=float)
        except Exception:
            qvec = np.frombuffer((query[:64].ljust(64)).encode('utf-8'), dtype='u1').astype(float)[:self._vec_dim]

        kind = self._vector_index[0]
        if kind == 'chroma':
            try:
                _, client, col = self._vector_index
                res = col.query(query_embeddings=[qvec.tolist()], n_results=topk)
                ids = res.get('ids', [[]])[0]
                scores = res.get('distances', [[]])[0]
                out = []
                for id_str, score in zip(ids, scores):
                    try:
                        out.append((int(id_str), float(score)))
                    except Exception:
                        continue
                return out
            except Exception:
                return []
        elif kind == 'faiss':
            try:
                _, index, id_list = self._vector_index
                import faiss
                import numpy as np
                q = np.array(qvec, dtype='float32').reshape(1, -1)
                scores, idxs = index.search(q, topk)
                out = []
                for s, i in zip(scores[0], idxs[0]):
                    out.append((int(i), float(s)))
                return out
            except Exception:
                return []
        else:
            # memory fallback
            try:
                _, data, _ = self._vector_index
                mat = np.stack([v for (_id, v) in data])
                sims = (mat @ qvec) / (np.linalg.norm(mat, axis=1) * (np.linalg.norm(qvec) + 1e-12))
                idxs = sims.argsort()[::-1][:topk]
                return [(int(i), float(sims[int(i)])) for i in idxs]
            except Exception:
                return []
