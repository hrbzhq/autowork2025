import sqlite3
from pathlib import Path
p = Path('.').resolve() / '.chromadb' / 'chroma.sqlite3'
print('DB path:', p)
if not p.exists():
    print('DB file not found')
    raise SystemExit(1)
con = sqlite3.connect(str(p))
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = cur.fetchone()[0]
        print(f"{t}: {cnt} rows")
    except Exception as e:
        print(f"Could not count rows in {t}:", e)

# try to dump small sample from collections or documents tables if present
for candidate in ('collections', 'documents', 'embeddings', 'metadatas', 'chunks'):
    if candidate in tables:
        print('\nSample rows from', candidate)
        try:
            cur.execute(f"SELECT * FROM {candidate} LIMIT 5")
            rows = cur.fetchall()
            for r in rows:
                print(r)
        except Exception as e:
            print('failed to read sample:', e)

con.close()
print('done')
