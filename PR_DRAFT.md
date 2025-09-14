# PR Draft: Agent Memory Toolkit

Title: feat(agent-memory): add cleanup, template-mapping, and embedding toolkit

Summary
-------
This PR adds a small, local-first toolkit for sanitizing and embedding an agent's file-backed memory. It includes:

- Historic cleanup and standardization utilities
- Aggressive template mapping to convert fragmentary sentences into concise action-style lessons
- Embedding generation (SentenceTransformer preferred, transformers fallback available)
- Unit tests and CI with caching for Hugging Face model files

Why
---
Agent memory files often accumulate role-prefixed lines and chain-of-thought fragments that are noisy for embeddings and retrieval. This toolkit standardizes the memory, keeps backups, and emits JSONL + embeddings ready for semantic search.

How to validate
---------------
Follow the reviewer checklist: see `PR_REVIEW_CHECKLIST.md` in the repo. Quick commands:

PowerShell (recommended):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python run_cleanup.py
python aggressive_template_map_and_writeback.py
pytest -q
python embed_memory.py
```

Suggested reviewers
-------------------
- @data-eng or the team member responsible for vector infra
- @dev-team for agent behavior and safety review

Labels
------
- enhancement
- infra/ci
- docs

Notes
-----
- The CI includes a cached embedding job; to exercise embedding in Actions, use workflow dispatch with `run_embed=true`.
- Backups are created automatically; do not override unless you intend to update the canonical memory.
