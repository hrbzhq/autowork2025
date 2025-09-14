# Reviewer Test Steps (detailed)

Follow these steps to fully validate the Agent Memory Toolkit changes on a local machine.

1) Prepare environment
```powershell
cd D:\study
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install pytest
```

2) Validate cleanup & mapping
```powershell
# backup current memory (extra safety)
copy agent_memory.txt agent_memory.txt.localbak

# run base cleanup and mapping
python run_cleanup.py
python aggressive_template_map_and_writeback.py

# inspect first 20 lines
Get-Content agent_memory.txt -TotalCount 20

# inspect jsonl
Get-ChildItem -Filter agent_memory_sanitized_*.jsonl
```

Validation expectations:
- `agent_memory.txt` should contain concise single-sentence lessons, capitalized and deduped.
- `agent_memory_sanitized_*.jsonl` should contain one JSON object per line with key `lesson`.

3) Run smoke tests and unit tests
```powershell
python standardize_and_test.py
python fix_prefix_and_test.py
pytest -q
```

Validation expectations:
- Tests pass (6 passed).
- Smoke test should run the agent and append a few short lessons to `agent_memory.txt` (confirm a few new "[Memory] Adding lesson:" messages in the agent run logs).

4) Generate embeddings
```powershell
python embed_memory.py
```

Validation expectations:
- `agent_memory_embeddings.jsonl` exists and contains objects with `id`, `lesson`, `vec_len`, `vec_summary`.
- Optionally, run a local similarity query (the script prints a demo query result).

5) CI validation (optional)
- Open the PR in GitHub and ensure `.github/workflows/ci.yml` triggers tests on PR. Optionally run workflow dispatch with `run_embed=true` to test embedding job (cache should speed downloads).

6) Rollback procedure (if needed)
```powershell
# restore backup
copy agent_memory.txt.backup.<ts> agent_memory.txt
# remove generated artifacts
Remove-Item agent_memory_sanitized_*.jsonl
Remove-Item agent_memory_embeddings.jsonl
```

If any step fails, capture the console logs and include them in the PR review comment.
