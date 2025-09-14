#!/usr/bin/env python3
"""
Aggressive template mapper
- Reads a source JSONL of lessons
- Applies template mappings (e.g. "they just expanded..." -> "Expanded ...")
- Shows before/after first 10
- Deduplicates, backs up existing memory, and writes agent_memory.txt + sanitized JSONL

Run: python d:\study\aggressive_template_map_and_writeback.py
"""
import re
import json
import shutil
import os
from datetime import datetime

SOURCE_JSONL = os.path.join(os.path.dirname(__file__), 'agent_memory_sanitized_20250911T172952.jsonl')
OUT_TXT = os.path.join(os.path.dirname(__file__), 'agent_memory.txt')


def load_jsonl(path):
    items = []
    if not os.path.exists(path):
        print(f"Source JSONL not found: {path}")
        return items
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and 'lesson' in obj:
                    items.append(str(obj['lesson']))
                else:
                    # try to coerce to string
                    items.append(str(obj))
            except Exception:
                # fallback: keep raw line
                items.append(line)
    return items


def backup_file(path):
    if not os.path.exists(path):
        return None
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dest = f"{path}.backup.{ts}"
    shutil.copy2(path, dest)
    return dest


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", ' ', s).strip()


def remove_role_prefixes(s: str) -> str:
    # Remove role-like prefixes such as "so the user is an autonomous agent, and"
    s = re.sub(r"^\s*(so\s+)?the\s+user\s+is\s+an\s+autonomous\s+agent\b[,;:\-\s]*", '', s, flags=re.I)
    s = re.sub(r"^\s*(so\s+)?the\s+team\b[,;:\-\s]*", '', s, flags=re.I)
    s = re.sub(r"^\s*(so\s+)?they\b[,;:\-\s]*", '', s, flags=re.I)
    return s


def map_templates(s: str) -> str:
    orig = s
    s = normalize_whitespace(s)
    s = s.strip('"')
    # remove common role prefixes
    s = remove_role_prefixes(s)
    # remove leading discourse
    s = re.sub(r'^(so|and|then|right|also)\b[,;:\-\s]*', '', s, flags=re.I)

    # common patterns
    patterns = [
        # they just X
        (r"\bthey\s+just\s+(.+)$", lambda m: m.group(1)),
        # the user just X
        (r"\bthe\s+user\s+just\s+(.+)$", lambda m: m.group(1)),
        # the user did an action called X
        (r"did(?:\s+an\s+action\s+called)?\s+['\"]?([^'\"]+)['\"]?$", lambda m: m.group(1)),
        # just X
        (r"^just\s+(.+)$", lambda m: m.group(1)),
        # (?:created|performed|expanded|reviewed|did|completed) X
        (r"\b(?:created|performed|expanded|reviewed|completed|executed|implemented|deployed|verified|configured)\s+(.+)$", lambda m: m.group(1)),
        # Step N of verifying a command -> Verify command (generalize)
        (r"step\s*\d+\s*of\s*(.+)$", lambda m: m.group(1)),
    ]

    lower = s.lower()
    for pat, fn in patterns:
        m = re.search(pat, lower, flags=re.I)
        if m:
            # extract substring from original (preserve casing better)
            try:
                extracted = fn(m).strip()
                # pick extracted from original using fuzzy search
                # fallback to extracted if not found
                # capitalize first letter
                extracted = re.sub(r"^[\'\"]+|[\'\"]+$", '', extracted)
                result = extracted[0].upper() + extracted[1:] if extracted else extracted
                # ensure ends without trailing ellipsis from template
                result = re.sub(r"\.\.\.+$", '', result).strip()
                return normalize_whitespace(result)
            except Exception:
                continue

    # if no pattern matched, as a last effort strip embedded metadata like "response': '..."
    # attempt to find a quoted fragment
    q = re.search(r"['\"]([A-Z][^'\"]{10,})['\"]", s)
    if q:
        candidate = q.group(1).strip()
        return candidate[0].upper() + candidate[1:]

    # default: return cleaned original, capitalized
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


def dedupe_preserve_order(items):
    seen = set()
    out = []
    for it in items:
        key = it.strip().lower()
        if len(key) < 8:
            # skip extremely short/empty lessons
            continue
        if key in seen:
            continue
        # avoid near-substring duplicates: if new item is substring of an existing item, skip
        skip = False
        for e in out:
            ek = e.strip().lower()
            if key in ek or ek in key:
                skip = True
                break
        if skip:
            continue
        seen.add(key)
        out.append(it.strip())
    return out


def main():
    items = load_jsonl(SOURCE_JSONL)
    if not items:
        print('No items loaded; aborting.')
        return

    mapped = [map_templates(x) for x in items]

    # show before/after first 10
    n = min(10, len(items))
    print('\n=== Before -> After (first {} entries) ==='.format(n))
    for i in range(n):
        print(f"{i+1:02d}. BEFORE: {items[i]!r}")
        print(f"    AFTER:  {mapped[i]!r}\n")

    # dedupe
    deduped = dedupe_preserve_order(mapped)

    # backups
    txt_backup = None
    if os.path.exists(OUT_TXT):
        txt_backup = backup_file(OUT_TXT)
        print(f"Backed up existing {OUT_TXT} -> {txt_backup}")

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_jsonl = os.path.join(os.path.dirname(__file__), f'agent_memory_sanitized_{ts}.jsonl')

    # write txt (one lesson per line)
    with open(OUT_TXT, 'w', encoding='utf-8') as f:
        for line in deduped:
            f.write(line + '\n')

    # write jsonl
    with open(out_jsonl, 'w', encoding='utf-8') as f:
        for line in deduped:
            json.dump({'lesson': line}, f, ensure_ascii=False)
            f.write('\n')

    print(f"Wrote {len(deduped)} deduplicated lessons to {OUT_TXT}")
    print(f"Wrote JSONL to {out_jsonl}")


if __name__ == '__main__':
    main()
