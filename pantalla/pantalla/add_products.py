import sqlite3

conn = sqlite3.connect('db.sqlite3')
c = conn.cursor()

# Agregar productos electrónicos
c.execute("INSERT INTO core_product (title, price, desc, category_id, img) VALUES (?, ?, ?, ?, ?)", ('Teclado Mecánico', '50.00', 'Teclado gaming con switches mecánicos', 1, ''))
c.execute("INSERT INTO core_product (title, price, desc, category_id, img) VALUES (?, ?, ?, ?, ?)", ('Audífonos Inalámbricos', '30.00', 'Audífonos Bluetooth con cancelación de ruido', 1, ''))
c.execute("INSERT INTO core_product (title, price, desc, category_id, img) VALUES (?, ?, ?, ?, ?)", ('Mouse Óptico', '15.00', 'Mouse ergonómico para oficina', 1, ''))

conn.commit()
print('Productos electrónicos agregados')
conn.close()