import os
import tempfile
from memory_store import MemoryStore


def test_add_and_get_context(tmp_path):
    p = tmp_path / 'mem.txt'
    m = MemoryStore(path=str(p))
    assert m.get_context() == 'No past experiences or lessons learned yet.'
    m.add_lesson('Always verify JSON format before parsing.')
    ctx = m.get_context()
    assert 'Always verify JSON format' in ctx


def test_find_similar_no_embeddings(tmp_path):
    p = tmp_path / 'mem.txt'
    m = MemoryStore(path=str(p))
    m.add_lesson('Check JSON formatting')
    # ensure embeddings file is not present
    emb = os.path.join(os.path.dirname(__file__), '..', 'agent_memory_embeddings.jsonl')
    if os.path.exists(emb):
        try:
            os.remove(emb)
        except Exception:
            pass
    res = m.find_similar('verify json', topk=2)
    # without embeddings, result may be empty list
    assert isinstance(res, list)