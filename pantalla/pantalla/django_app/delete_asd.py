import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Eliminar productos con title 'asd'
c.execute("DELETE FROM core_product WHERE title = 'asd'")
conn.commit()

print('Productos asd eliminados')
conn.close()