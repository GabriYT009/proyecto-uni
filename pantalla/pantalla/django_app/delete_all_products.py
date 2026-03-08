import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Eliminar todos los productos
c.execute("DELETE FROM core_product")
conn.commit()

print('Todos los productos eliminados')
conn.close()