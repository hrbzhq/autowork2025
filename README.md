# Agent memory cleanup & embedding toolkit

Small toolkit to clean, standardize and embed an agent's file-backed memory. Includes scripts for historic sanitization, aggressive template mapping, smoke tests, and local embedding (SentenceTransformer or transformers fallback).

## Purpose
- Remove role-like and chain-of-thought text from memory entries.
- Convert fragmentary templates ("they just...", "the user... just...") to concise action-style lessons suitable for storage and embeddings.
- Produce JSONL and embedding outputs ready for semantic search or clustering.

## Files / Scripts
- `run_cleanup.py` — backup original memory file, aggressive sanitize, export JSONL.
- `standardize_and_test.py` — remove role-like prefixes and run a smoke test to validate future writes.
- `fix_prefix_and_test.py` — remove leading conjunctions and smoke-test agent writes.
- `aggressive_template_map_and_writeback.py` — aggressive template mapping to action-style sentences; shows before/after (first 10), dedupes and writes `agent_memory.txt` and timestamped JSONL.
- `embed_memory.py` — produces embeddings for `agent_memory.txt`; tries `sentence-transformers`, falls back to `transformers` mean-pooling encoder, and falls back to deterministic pseudo-vectors if neither available.
- `test_agent_v1.py` — unit tests for parsing & memory behaviors.

## Recommended run order
1. `run_cleanup.py` (historic sanitize + backups)
2. `aggressive_template_map_and_writeback.py` (template mapping + dedupe)
3. `standardize_and_test.py` / `fix_prefix_and_test.py` (smoke tests)
4. `embed_memory.py` (generate embeddings)

## Dependencies & environment
- Recommended: use a virtual environment.

PowerShell example (one-liner):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
```

`requirements.txt` (included) contains:
- sentence-transformers==2.2.2
- numpy

Notes:
- `sentence-transformers` is preferred (model: `all-MiniLM-L6-v2`). If package conflicts occur, the toolkit falls back to a `transformers` based mean-pooling encoder (auto-downloads same model). If network access is restricted, a simulated embedding path is available but not recommended.

Optional vector DB backends
- Chroma: recommended for developer convenience and persistence. Install with `pip install chromadb` and optionally `chromadb[ray]` for advanced setups.
- FAISS: high-performance local vector index. On Windows prefer `faiss-cpu` via conda or appropriate wheel; installing on Windows via pip can be tricky.

If you intend to use a local vector DB for retrieval (recommended for medium/large memory), install one of the above. The agent will auto-detect Chroma first, then FAISS; otherwise it uses an in-memory fallback.

CI / caching hints
- Model weights (SentenceTransformer/transformers) are large; cache the HF model directory in CI. For GitHub Actions, cache `~/.cache/huggingface` and `~/.cache/torch` (or relevant platform paths) to avoid repeated downloads.
- Example GitHub Actions snippet (conceptual):

```yaml
# - name: Cache huggingface models
#   uses: actions/cache@v4
#   with:
#     path: |
#       ~/.cache/huggingface
#       ~/.cache/torch
#     key: hf-models-${{ runner.os }}-${{ hashFiles('**/requirements.txt') }}
#     restore-keys: |
#       hf-models-${{ runner.os }}-
```

Notes on installing FAISS/Chroma in CI:
- Chroma can be installed with `pip install chromadb` (but may add system-level deps for some features).
- FAISS is often easier via conda (e.g., `conda install -c pytorch faiss-cpu`) — consider a separate job or using a container that already contains faiss.

GitHub Actions example
- A sample workflow is included at `.github/workflows/ci-embed.yml`.
- The workflow runs unit tests on push/PR. It also exposes an optional `workflow_dispatch` job `embed` that will generate `agent_memory_embeddings.jsonl` (useful for one-off embedding builds or regenerations). The `embed` job caches huggingface/torch caches and uploads the embedding JSONL as an artifact.

To manually trigger embedding in GitHub Actions:
1. Push your branch and open the Actions tab. Find the workflow `CI - Tests & Optional Embedding` and click `Run workflow`.
2. The `embed` job will run (it depends on tests passing) and upload `agent_memory_embeddings.jsonl` as an artifact.

## Expected outputs
- `agent_memory.txt` — cleaned, deduplicated lessons (one per line)
- `agent_memory_sanitized_<ts>.jsonl` — timestamped JSONL backup of sanitized lessons
- `agent_memory_embeddings.jsonl` — per-lesson embedding summary (id, lesson, vec_len, vec_summary)

## Troubleshooting
- huggingface-hub / transformers version conflicts: install in a fresh venv or use the transformers fallback. If you see errors about `cached_download` or similar, rebuild venv and ensure `huggingface-hub` is compatible with installed transformers.
- Model download fails: ensure network access or pre-download the model weights into HF cache.

## Backup & rollback
- Every script that rewrites `agent_memory.txt` creates a `.backup.<ts>` copy in the same folder. To rollback: replace `agent_memory.txt` with the most recent `agent_memory.txt.backup.<ts>` and remove generated JSONL/embedding files.

## Extending
- Import `agent_memory_sanitized_*.jsonl` into a vector DB (FAISS / Chroma / Pinecone) for semantic retrieval. The `agent_memory_embeddings.jsonl` file contains summarized vectors (first 8 dims) to validate encoding quickly.

## Tests
- Run: `pytest -q` (requires pytest installed). Tests cover JSON extraction and memory write/cleanup helpers.

## License & attribution
Add license and author information here if you plan to publish this repository (optional).

---
If you'd like, I can also create a small `Makefile`/`tasks.json` or a CI snippet to automate checks and embedding generation.
# Simplified MCP Agent V1

This is a minimal local-first implementation of an MCP (Mission-Command-Plan) loop with basic recursive optimization and local model routing.

Files:
- `agent_v1.py`: The main agent script. It uses a local Ollama API if available; otherwise it simulates model responses.
- `requirements.txt`: Python dependencies.
- `agent_memory.txt`: (created when the agent learns lessons) Stores lessons learned across runs.

Quick start (PowerShell):

```powershell
python -m pip install -r requirements.txt
python agent_v1.py --mission "Your mission here"
```

Notes:
- Adjust `SIMPLE_MODEL` and `COMPLEX_MODEL` in `agent_v1.py` to match the local model names you pulled with Ollama.
- If Ollama isn't running, the script will fall back to simulated answers so you can test the loop logic.

Docker (dev image)
-------------------

Build a small development image and optionally push it to a registry. A helper PowerShell script is provided at `scripts/build-and-push-dev.ps1`.

Local build example (PowerShell):

```powershell
# Build only
.
# From the repo root:
./scripts/build-and-push-dev.ps1

# Build and push (set DO_PUSH=1 and credentials):
$env:DO_PUSH='1'; $env:DOCKER_USERNAME='youruser'; $env:DOCKER_PASSWORD='yourpassword'; ./scripts/build-and-push-dev.ps1
```

By default the script builds `hrbzhq/autowork2025:dev`. Override with `IMAGE_NAME` environment variable.

