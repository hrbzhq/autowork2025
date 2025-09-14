# PR Review Checklist: Agent Memory Toolkit

Use this checklist when reviewing the PR that introduces the agent-memory cleanup, standardization and embedding toolkit.

## ✅ Memory 清理与标准化
- [ ] 是否执行了角色前缀与模板映射清理（`aggressive_template_map_and_writeback.py`）？
- [ ] 是否保留并提交了备份文件（例如 `agent_memory.txt.backup.<ts>`）？
- [ ] 是否写回了 deduped 的 `agent_memory.txt` 与 timestamped `agent_memory_sanitized_*.jsonl`？
- [ ] 是否确认没有把 chain-of-thought 或敏感中间状态写入 memory？

## ✅ Embedding 生成
- [ ] 是否使用真实 encoder（`sentence-transformers` 或 `transformers` fallback）生成 embeddings？
- [ ] 是否生成了 `agent_memory_embeddings.jsonl`（或 CI artifact）？
- [ ] 是否展示了至少一个示例相似度检索结果以验证效果？

## ✅ 测试覆盖
- [ ] 是否包含单元测试（`test_agent_v1.py`）？
- [ ] 本地或 CI 中 `pytest` 是否通过（示例：`6 passed`）？

## ✅ CI 工作流
- [ ] 是否包含 `.github/workflows/ci.yml`（运行测试）？
- [ ] 是否包含 `.github/workflows/ci-cache.yml`（缓存 HF 模型与 pip）以加速 embedding 作业？

## ✅ 文档与提交说明
- [ ] 是否包含 `README.md`，说明运行顺序、依赖与回滚策略？
- [ ] 是否包含 `PR_DESCRIPTION.md` 与 `PR_COMMIT_MSG.md` 供提交/审阅参考？

## ✅ 回滚与安全性
- [ ] 是否在文档中明确了回滚步骤（用最近的 `.backup.<ts>` 恢复）？
- [ ] 是否对可能的依赖冲突（huggingface-hub 等）提供了建议（使用 venv）？

## Quick validation commands (local)
```powershell
# create venv, install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -r requirements.txt

# run cleanup and mapping
python run_cleanup.py
python aggressive_template_map_and_writeback.py

# run tests
pytest -q

# generate embeddings (optional)
python embed_memory.py
```

## Reviewer notes / Tips
- Check the first 10 lines of `agent_memory.txt` before/after mapping for obvious template cleanup.
- Confirm `agent_memory_sanitized_*.jsonl` exists and contains only `{"lesson": "..."}` JSON objects.
- If embedding step fails in CI, re-run with cached model or inspect `huggingface-hub` conflict notes in README.
