PR: Add agent-memory cleanup, standardization, and embedding toolkit

Summary
-------
This change introduces a small toolkit to clean up historical agent memory stored in a plaintext `agent_memory.txt` and produce embeddings for semantic retrieval. It includes scripts to sanitize legacy entries, aggressively map template-like fragments to concise action-style lessons, run smoke tests against the agent to validate future writes, and produce embeddings using either SentenceTransformer or a transformers-based fallback.

Files added/changed
------------------
- `aggressive_template_map_and_writeback.py` — aggressive template mapping and writeback (new)
- `embed_memory.py` — embedding generation with fallback encoders (new)
- `README.md` — documentation (new)
- `PR_DESCRIPTION.md` — this file (new)

Also present in the repo (already added earlier in the project):
- `run_cleanup.py`, `standardize_and_test.py`, `fix_prefix_and_test.py`, `test_agent_v1.py`, `agent_v1.py`

How to validate (quick)
-----------------------
1. Backup current memory: `cp agent_memory.txt agent_memory.txt.bak` (or use the backups created by scripts).
2. Run `python aggressive_template_map_and_writeback.py` and confirm the terminal shows Before->After diffs for the first 10 entries.
3. Run `python embed_memory.py` inside a virtual environment (see README). Confirm `agent_memory_embeddings.jsonl` is produced and a demo query prints top-k similar lessons.

Rollback
--------
Restore `agent_memory.txt` from the `.backup.<ts>` files created by the scripts, and delete generated JSONL/embedding files.

Notes
-----
- The embed script prefers `sentence-transformers`, but falls back to `transformers` mean pooling to avoid excessive dependency version issues. If you prefer a strict dependency set, consider pinning `huggingface-hub` for full compatibility.
