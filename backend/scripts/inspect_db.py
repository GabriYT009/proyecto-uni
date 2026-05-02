import os
import json
import sqlite3
from pathlib import Path

# Configurar Django environment
import django
from django.conf import settings

# Ajustar path para que Django pueda cargar settings
BASE_DIR = Path(__file__).resolve().parent.parent
os.chdir(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()

print('--- Django DATABASES ---')
print(json.dumps(settings.DATABASES, indent=2, default=str))

# Ruta al archivo sqlite dentro del repo
sqlite_path = Path(BASE_DIR) / 'django_app' / 'db.sqlite3'
print('--- sqlite path ---')
print(str(sqlite_path))
print('Exists:', sqlite_path.exists())

if sqlite_path.exists():
    try:
        conn = sqlite3.connect(str(sqlite_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print('--- Tables ---')
        print(json.dumps(tables, indent=2))
    except Exception as e:
        print('Error reading sqlite:', e)
else:
    print('No sqlite file found')

print('\nDone')
