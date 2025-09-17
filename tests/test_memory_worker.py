import time
from memory_store import MemoryStore


def test_background_worker_runs(tmp_path):
    p = tmp_path / 'mem.txt'
    m = MemoryStore(path=str(p))
    m.add_lesson('Test lesson for worker embedding')
    # give worker a brief moment to pick up the job
    time.sleep(0.5)
    # stop worker gracefully
    m.stop_worker(timeout=0.5)
    # ensure file still contains our lesson
    with open(str(p), 'r', encoding='utf-8') as f:
        data = f.read()
    assert 'Test lesson for worker embedding' in data
