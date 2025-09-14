import os
import re
import shutil
import datetime
from agent_v1 import SimpleMemory, SimplifiedAgent


def fix_leading_conjunction(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    s = s.strip()
    # remove common leading conjunctions or filler words
    s = re.sub(r'^(and|but|so|then|right|also)\b[:,\s-]*', '', s, flags=re.IGNORECASE)
    # remove repeated leading punctuation/spaces
    s = re.sub(r'^[-:\s]+', '', s)
    return s.strip()


def main():
    p = os.path.join(os.getcwd(), 'agent_memory.txt')
    if not os.path.exists(p):
        print('[fix_prefix] No memory file found; aborting.')
        return
    with open(p, 'r', encoding='utf-8') as f:
        orig_lines = [l.rstrip('\n') for l in f.readlines() if l.strip()]

    print('[fix_prefix] First 10 before:')
    for i, ln in enumerate(orig_lines[:10], 1):
        print(f'{i}. {ln}')

    # backup
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    backup = os.path.join(os.getcwd(), f'agent_memory_prefixbackup_{ts}.txt')
    shutil.copy2(p, backup)
    print(f'[fix_prefix] Backed up to {backup}')

    # process lines
    new_lines = []
    seen = set()
    for ln in orig_lines:
        fixed = fix_leading_conjunction(ln)
        if not fixed or len(fixed) < 8:
            continue
        if fixed in seen:
            continue
        seen.add(fixed)
        new_lines.append(fixed)

    # write back
    with open(p, 'w', encoding='utf-8') as f:
        for ln in new_lines:
            f.write(ln + '\n')

    print('\n[fix_prefix] First 10 after:')
    for i, ln in enumerate(new_lines[:10], 1):
        print(f'{i}. {ln}')

    # smoke test: run agent and detect new lessons
    mem_before = SimpleMemory(path=p)
    pre_count = len(mem_before.lessons)
    print(f'\n[fix_prefix] Pre-run lessons count: {pre_count}')

    agent = SimplifiedAgent(mission='Run a small validation for prefix-clean test')
    agent.run()

    mem_after = SimpleMemory(path=p)
    post_count = len(mem_after.lessons)
    print(f'[fix_prefix] Post-run lessons count: {post_count}')
    added = mem_after.lessons[pre_count:]
    if added:
        print('[fix_prefix] Newly added lessons:')
        for ln in added:
            print('-', ln)
    else:
        print('[fix_prefix] No new lessons were added (or deduped).')


if __name__ == '__main__':
    main()
