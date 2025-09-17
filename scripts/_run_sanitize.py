from memory_store import MemoryStore
ms = MemoryStore()
print('--- BEFORE (first 40 lines) ---')
try:
    with open(ms.path,'r',encoding='utf-8') as f:
        lines = [l.rstrip('\n') for l in f]
except Exception:
    lines = []
for i,l in enumerate(lines[:40]):
    print(f'{i+1:03d}: {l}')
ms.sanitize_existing()
print('\n--- AFTER (first 40 lines) ---')
try:
    with open(ms.path,'r',encoding='utf-8') as f:
        lines2 = [l.rstrip('\n') for l in f]
except Exception:
    lines2 = []
for i,l in enumerate(lines2[:40]):
    print(f'{i+1:03d}: {l}')
print('\nTotal before:', len(lines), 'Total after:', len(lines2))
