import os
import re
import shutil
import datetime
import sys
from agent_v1 import SimpleMemory, SimplifiedAgent


def remove_role_prefix(s: str) -> str:
    if not s or not isinstance(s, str):
        return s
    orig = s
    s = s.strip()
    # common role/intro prefixes to remove
    patterns = [
        r'^(so\s+)?the user is an autonomous agent[,\s:;-]*',
        r'^(so\s+)?the user is an autonomous agent who[,\s:;-]*',
        r'^(so\s+)?the user is an autonomous agent that[,\s:;-]*',
        r'^(so\s+)?the user is an autonomous agent and[,\s:;-]*',
        r'^(so\s+)?the user[,\s:;-]*',
        r'^(so[,\s]+)',
        r'^(the user is[,\s]+)',
    ]
    for p in patterns:
        s2 = re.sub(p, '', s, flags=re.IGNORECASE).strip()
        if s2 != s:
            s = s2
    # collapse spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def standardize_line(s: str) -> str | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    s = remove_role_prefix(s)
    # take first sentence
    frag = re.split(r'[\.\!\?\n]', s)[0].strip()
    frag = re.sub(r'\s+', ' ', frag)
    if not frag or len(frag) < 8:
        return None
    # truncate to 100 chars
    if len(frag) > 100:
        frag = frag[:100].rsplit(' ', 1)[0] + '...'
    return frag


def main():
    p = os.path.join(os.getcwd(), 'agent_memory.txt')
    if not os.path.exists(p):
        print('[standardize] No memory file found; aborting.')
        return
    # read current lines
    with open(p, 'r', encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f.readlines() if l.strip()]

    print('[standardize] First 10 original lines:')
    for i, ln in enumerate(lines[:10], 1):
        print(f'{i}. {ln}')

    # standardize
    new_lines = []
    seen = set()
    for ln in lines:
        cand = standardize_line(ln)
        if not cand:
            continue
        if cand in seen:
            continue
        seen.add(cand)
        new_lines.append(cand)

    print('\n[standardize] First 10 standardized lines:')
    for i, ln in enumerate(new_lines[:10], 1):
        print(f'{i}. {ln}')

    # backup original
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    backup = os.path.join(os.getcwd(), f'agent_memory_prestd_{ts}.txt')
    shutil.copy2(p, backup)
    print(f'[standardize] Backed up original to: {backup}')

    # write standardized back
    with open(p, 'w', encoding='utf-8') as f:
        for ln in new_lines:
            f.write(ln + '\n')

    print('[standardize] Wrote standardized memory file.')

    # Run the agent to produce new reflections (smoke test)
    pre_count = len(new_lines)
    print(f'[standardize] Pre-run lesson count: {pre_count}')
    agent = SimplifiedAgent(mission='Run a short validation mission to produce a reflection.')
    agent.run()

    # reload memory and find new entries
    mem = SimpleMemory()
    post_count = len(mem.lessons)
    print(f'[standardize] Post-run lesson count: {post_count}')
    added = mem.lessons[pre_count:]
    if added:
        print('[standardize] Newly added lessons:')
        for ln in added:
            print('-', ln)
    else:
        print('[standardize] No new lessons were added (or they were deduped).')


if __name__ == '__main__':
    main()
