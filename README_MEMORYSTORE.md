MemoryStore 使用说明（简短）

- 文件: `memory_store.py` 提供 `MemoryStore`，文件路径默认为 `agent_memory.txt`。
- `add_lesson(lesson: str)`：添加简短、清洗后的 lesson，会追加到 `agent_memory.txt` 并异步加入嵌入队列。
- `get_context()`：返回可注入到 LLM prompt 的历史要点文本。
- `embed_lessons()`：手动触发嵌入生成，会尝试：
  1. 优先使用 `sentence-transformers`（`all-MiniLM-L6-v2`）
  2. 回退到 `transformers` + AutoModel（mean-pooling）
  3. 若都不可用，写入确定性伪嵌入
- 异步工作线程会在内存初始化时启动（后台守护），在添加 lesson 后自动刷新嵌入（best-effort）。

如何在本地获取真实嵌入（推荐）

1. 创建并激活虚拟环境：
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 手动运行嵌入（如果不想等待 agent 触发）：
```powershell
python .\embed_memory.py
```

注意：如果网络或依赖问题导致 `sentence-transformers` 无法使用，系统会回退到较慢但更兼容的 `transformers` 路径，或写入伪向量以保证功能连续性。
