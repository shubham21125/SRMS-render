import os
import sys
import django
import sqlite3
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StudentResultManagement.settings')
django.setup()

from django.apps import apps
from django.db import connection

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

print("="*80)
print("ALL SQLITE TABLES AND ROW COUNTS")
print("="*80)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = [r[0] for r in cur.fetchall()]
table_counts = {}
for t in tables:
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    cnt = cur.fetchone()[0]
    table_counts[t] = cnt
    print(f"{t:45}: {cnt:>6} rows")

print("\n" + "="*80)
print("TABLE SCHEMAS (PRAGMA table_info & PRAGMA foreign_key_list & PRAGMA index_list)")
print("="*80)
resultapp_tables = [t for t in tables if t.startswith('resultapp_')]

table_details = {}
for t in resultapp_tables:
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = cur.fetchall() # cid, name, type, notnull, dflt_value, pk
    
    cur.execute(f'PRAGMA foreign_key_list("{t}")')
    fks = cur.fetchall() # id, seq, table, from, to, on_update, on_delete, match
    
    cur.execute(f'PRAGMA index_list("{t}")')
    indexes = cur.fetchall() # seq, name, unique, origin, partial
    
    index_details = []
    for idx in indexes:
        idx_name = idx[1]
        cur.execute(f'PRAGMA index_info("{idx_name}")')
        idx_cols = [c[2] for c in cur.fetchall()]
        index_details.append({
            'name': idx_name,
            'unique': bool(idx[2]),
            'columns': idx_cols
        })
        
    table_details[t] = {
        'count': table_counts[t],
        'columns': cols,
        'foreign_keys': fks,
        'indexes': index_details
    }

print(json.dumps(table_details, indent=2))
