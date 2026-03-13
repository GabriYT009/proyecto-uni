import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Insertar categorías
c.execute("INSERT OR IGNORE INTO core_category (name, slug, description) VALUES (?, ?, ?)", ('Electrónica', 'electronica', 'Productos electrónicos'))
c.execute("INSERT OR IGNORE INTO core_category (name, slug, description) VALUES (?, ?, ?)", ('Ropa', 'ropa', 'Ropa y accesorios'))
c.execute("INSERT OR IGNORE INTO core_category (name, slug, description) VALUES (?, ?, ?)", ('Hogar', 'hogar', 'Artículos para el hogar'))

conn.commit()
conn.close()

print('Categorías insertadas')