# PR Review Comments: Agent Memory Toolkit

Use these ready-made comments to speed up PR reviews. Paste into GitHub review as needed and adjust specifics (file names, timestamps) per PR.

-- Approve template (happy path)

LGTM ✅
- Changes are scoped and documented in `README.md`.
- Tests pass locally and in CI (`pytest` → 6 passed).
- Backup behavior verified: scripts create `agent_memory.txt.backup.<ts>` before modifications.
- Embedding script produces `agent_memory_embeddings.jsonl` when run locally/CI (or available as artifact).

Approve once the author confirms generated backup files will be preserved in release branch.

-- Request changes (problem example)

Please address the following before I can approve:
1. The mapping in `aggressive_template_map_and_writeback.py` produced some lowercased lessons (e.g., "Performed an action called define target audience and"); please normalize capitalization and remove trailing fragments/ellipses.
2. Add a short unit test that asserts `SimpleMemory.add_lesson()` does not store strings containing obvious chain-of-thought markers (e.g., "I thought", "I need to").
3. CI caching workflow is present; please ensure the cache key accounts for model name in case model changes in future.

-- Security/rollback probe comment

Quick security check:
- Confirm no secrets or API keys are stored in the repo.
- Confirm that `agent_memory.txt` backups are not accidentally committed with sensitive user data. If they are, add a filter to redact or exclude from commits.

-- Request for verification (for the author to run and paste results)

Please paste the following outputs here before requesting final review:
- `head -n 10 agent_memory.txt` (post-mapping)
- `ls -1 agent_memory_sanitized_*.jsonl` (to confirm JSONL files)
- `python -m pytest -q` output
- `python embed_memory.py` demo snippet showing top-3 results for query "verify json format" or a note that embedding run was skipped in CI (if run_embed was false)
