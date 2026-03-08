# db_config.py

import mysql.connector

# Configuración de tu base de datos SOLUCIONARTE
DB_CONFIG = {
    'user': 'root', 
    'password': '123456', # Asegúrate de que esta sea tu contraseña de MySQL
    'host': 'localhost',
    'database': 'solucionarte', # ¡Nombre actualizado!
    'port': 3306,
    'raise_on_warnings': True
}

def get_db_connection():
    """Establece y devuelve la conexión a la BD."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"--- ERROR CRÍTICO DE CONEXIÓN A MYSQL ---")
        print(f"Código de error: {err.errno}")
        print(f"Mensaje de error: {err.msg}")
        print("------------------------------------------")
        return None

def get_last_insert_id(cursor):
    """Obtiene el ID de la última inserción."""
    # Usamos la consulta nativa de MySQL para obtener el último ID en la misma sesión
    cursor.execute("SELECT LAST_INSERT_ID()")
    last_id = cursor.fetchone()[0]
    return last_id