Commit message (suggested):
feat: add agent-memory cleanup, template mapping, and embedding toolkit

PR description (suggested):
This PR introduces a small toolkit to sanitize and standardize agent memory stored in a plaintext `agent_memory.txt`, map template-like fragments into concise action-style lessons, validate agent writes via smoke tests, and generate embeddings for semantic retrieval.

Key files added:
- `aggressive_template_map_and_writeback.py` — map templates and writeback with backups
- `embed_memory.py` — embedding generation with sentence-transformers or transformers fallback
- `README.md` — documentation and runbook
- `PR_DESCRIPTION.md` — change summary
- `requirements.txt` — reproducible dependencies
- `.github/workflows/ci.yml` — CI: run tests + optional embedding job

Validation steps:
1. Run `python aggressive_template_map_and_writeback.py` and verify the Before/After diffs for the first 10 lessons.
2. Run `pytest -q` and ensure all tests pass.
3. (Optional) Create a workflow dispatch with `run_embed=true` to test embedding generation in CI.

Rollback:
- Restore `agent_memory.txt` from the backup file `agent_memory.txt.backup.<ts>` created by the scripts.
- Delete generated JSONL/embedding files.
