import inspect
import chromadb
import importlib
from pathlib import Path
print('chromadb version =', getattr(chromadb, '__version__', 'unknown'))
print('chromadb __file__ =', getattr(chromadb, '__file__', None))
print('\nTop-level attributes:')
print([a for a in dir(chromadb) if not a.startswith('_')])

# try to find Client class
Client = getattr(chromadb, 'Client', None)
print('\nClient object:', Client)
if Client:
    try:
        print('Client signature:', inspect.signature(Client))
    except Exception as e:
        print('Could not get signature:', e)

# inspect chromadb.config
cfg = importlib.import_module('chromadb.config')
print('\nchromadb.config attributes:')
print([a for a in dir(cfg) if not a.startswith('_')])

# check for new persistence APIs
for name in ['PersistentClient', 'Settings', 'API', 'Sqlite', 'DuckDB', 'DuckDBPersist', 'ChromaDB']:
    if hasattr(chromadb, name) or hasattr(cfg, name):
        print('Found', name)

# try to inspect client code file
try:
    import inspect
    src = inspect.getsource(Client)
    print('\n----- Client source (first 2000 chars) -----\n')
    print(src[:2000])
except Exception as e:
    print('Could not get Client source:', e)

# also list chromadb.api
try:
    api = importlib.import_module('chromadb.api')
    print('\nchromadb.api attrs:', [a for a in dir(api) if not a.startswith('_')])
except Exception as e:
    print('chromadb.api import failed:', e)

print('\nDone')
