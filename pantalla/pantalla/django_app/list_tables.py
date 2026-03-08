import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()
c.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = [row[0] for row in c.fetchall()]
print('Tablas:', tables)
conn.close()