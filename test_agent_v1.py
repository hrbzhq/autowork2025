import json
import os
import tempfile
import pytest
from agent_v1 import SimplifiedAgent, SimpleMemory


def test_extract_json_array_and_parse():
    agent = SimplifiedAgent(mission="Test mission")
    # well-formed array
    text = 'Here is the array: ["a","b","c"] and some trailing text'
    arr = agent._extract_json_array(text)
    assert arr is not None
    parsed = json.loads(arr)
    assert isinstance(parsed, list) and parsed == ["a", "b", "c"]

    # nested arrays
    text2 = 'prefix ["x", {"response": "y"}, "z"] suffix'
    arr2 = agent._extract_json_array(text2)
    assert arr2 is not None
    parsed2 = json.loads(arr2)
    assert parsed2[0] == "x"
    assert isinstance(parsed2[1], dict)


def test_parse_json_list_or_fallback_with_dict_elements():
    agent = SimplifiedAgent(mission="Test mission")
    resp = '[{"response": "R1"}, {"lesson": "L2"}, "S3"]'
    items = agent._parse_json_list_or_fallback(resp, fallback_count=5)
    assert items[0] == "R1"
    assert items[1] == "L2"
    assert items[2] == "S3"


def test_simplememory_add_and_aggressive_sanitize(tmp_path):
    p = tmp_path / "mem.txt"
    mem = SimpleMemory(path=str(p))
    # add some noisy entries
    mem.add_lesson('{"lesson": "  A concise lesson about testing.  "}')
    mem.add_lesson('Keep tasks small and verify outputs.')
    mem.add_lesson('Short')  # should be rejected
    # write a noisy raw dict line to file to simulate legacy noisy entry
    with open(p, 'a', encoding='utf-8') as f:
        f.write("{'response': 'This is an old verbose thought process that should be sanitized.'}\n")
        f.write('''```\ncode block\n```\n''')
    # aggressive sanitize
    mem.aggressive_sanitize_file()
    # reload
    mem._load()
    # all lessons in memory should be readable strings and length >= 12
    assert all(isinstance(s, str) for s in mem.lessons)
    assert all(len(s) >= 12 for s in mem.lessons)
    # ensure short entry was rejected
    assert not any(s == 'Short' for s in mem.lessons)


if __name__ == '__main__':
    pytest.main([__file__])
