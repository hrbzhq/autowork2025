import os
import sys
import json
import re
from agent_v1 import SimpleMemory


def main():
    p = os.path.join(os.getcwd(), 'agent_memory.txt')
    mem = SimpleMemory(path=p)
    print('[Runner] Loaded memory file:', p)

    # 1) Backup original memory to timestamped JSONL
    import shutil, datetime
    ts = datetime.datetime.now().strftime('%Y%m%dT%H%M%S')
    backup_txt = os.path.join(os.getcwd(), f'agent_memory_backup_{ts}.txt')
    backup_jsonl = os.path.join(os.getcwd(), f'agent_memory_backup_{ts}.jsonl')
    if os.path.exists(p):
        shutil.copy2(p, backup_txt)
        # write original lines as JSONL for safe archival
        try:
            with open(p, 'r', encoding='utf-8') as fin, open(backup_jsonl, 'w', encoding='utf-8') as jout:
                for ln in fin:
                    ln_s = ln.rstrip('\n')
                    jout.write(json.dumps({"original": ln_s}, ensure_ascii=False) + "\n")
        except Exception as e:
            print('[Runner] Warning: failed to write JSONL backup:', e)
        print(f'[Runner] Backed up original memory to: {backup_txt} and {backup_jsonl}')
    else:
        print('(no memory file found)')
        return

    # 2) Run aggressive sanitize first (existing aggressive function)
    mem.aggressive_sanitize_file()
    mem._load()

    # 3) Enhanced standardization pass: remove leading discourse tokens, take first sentence, truncate to 100 chars, dedupe
    def standardize_text(s: str) -> str | None:
        if not s or not isinstance(s, str):
            return None
        s = s.strip()
        # remove common leading tokens
        s = re.sub(r'^(okay[,\s]+|ok[,\s]+|alright[,\s]+|so[,\s]+|right[,\s]+|well[,\s]+)', '', s, flags=re.IGNORECASE)
        # remove surrounding quotes
        s = s.strip('"\'')
        # take first sentence-like fragment
        frag = re.split(r'[\.\!\?\n]', s)[0].strip()
        frag = re.sub(r'\s+', ' ', frag)
        if not frag or len(frag) < 8:
            return None
        # truncate to 100 chars without cutting words
        if len(frag) > 100:
            frag = frag[:100].rsplit(' ', 1)[0] + '...'
        return frag

    # build standardized list from mem.lessons (already cleaned by aggressive_sanitize_file)
    standardized = []
    seen = set()
    for ln in mem.lessons:
        cand = standardize_text(ln)
        if not cand:
            continue
        if cand in seen:
            continue
        seen.add(cand)
        standardized.append(cand)

    # 4) Write standardized file and JSONL sanitized version
    sanitized_txt = p
    sanitized_jsonl = os.path.join(os.getcwd(), f'agent_memory_sanitized_{ts}.jsonl')
    try:
        with open(sanitized_txt, 'w', encoding='utf-8') as fout, open(sanitized_jsonl, 'w', encoding='utf-8') as jout:
            for ln in standardized:
                fout.write(ln.replace('\n', ' ') + '\n')
                jout.write(json.dumps({"lesson": ln}, ensure_ascii=False) + "\n")
        print(f'[Runner] Wrote sanitized memory to: {sanitized_txt} and {sanitized_jsonl}')
    except Exception as e:
        print('[Runner] Failed to write sanitized outputs:', e)

    # 5) Print a short diff summary and head of sanitized file
    print('=== Standardized lessons (first 50) ===')
    for i, ln in enumerate(standardized[:50]):
        print(f'{i+1}. {ln}')
    print(f'=== Total sanitized lessons: {len(standardized)} ===')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('[Runner] Error during cleanup:', e)
        sys.exit(1)
from agent_v1 import SimpleMemory
import pathlib

m = SimpleMemory()
print('[INFO] Loaded memory, current lessons count:', len(m.lessons))
# perform aggressive cleanup
m.aggressive_sanitize_file()
# reload and print
m._load()
print('---MEMORY START---')
p = pathlib.Path('agent_memory.txt')
if p.exists():
    print(p.read_text(encoding='utf-8'))
else:
    print('[No memory file found]')
print('---MEMORY END---')
