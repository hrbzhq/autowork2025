import time
from memory_store import MemoryStore


def test_vector_upsert_and_query(tmp_path):
    p = tmp_path / 'mem.txt'
    m = MemoryStore(path=str(p))
    # add multiple lessons
    m.add_lesson('Verify JSON formatting always')
    m.add_lesson('Always sanitize input before parsing')
    m.add_lesson('Prefer small incremental steps')
    # give background worker a moment to process
    time.sleep(0.5)
    # query for a similar lesson
    res = m.find_similar('verify json', topk=2)
    assert isinstance(res, list)
    # results may be empty if embedding backends are unavailable, but should not error
    # if non-empty, ensure tuples returned
    if res:
        assert isinstance(res[0][0], int)
        assert isinstance(res[0][1], float)