from flask import Flask, render_template, request
from db_config import get_db_connection
import sys # Para manejo de errores

app = Flask(__name__)

# Configuración de sesión temporal (necesaria para Flask, aunque no la usemos aquí)
app.secret_key = 'tu_clave_secreta_aqui'

@app.route('/')
def index():
    """Ruta principal que muestra el formulario de creación de cliente."""
    # Nombre del archivo HTML debe ser correcto (crear_cliente.html)
    return render_template('crear_cliente.html')

@app.route('/procesar_cliente', methods=['POST'])
def procesar_cliente():
    """
    Ruta para procesar la inserción del cliente.
    Realiza una inserción en dos pasos (cliente y especialización) en una transacción.
    """
    
    conn = get_db_connection()
    if conn is None:
        # Si la conexión falla, se muestra un error al usuario.
        return "<h1>❌ Error 500: Falló la conexión a la base de datos</h1><p>Verifique db_config.py y su servidor MySQL.</p>", 500
    
    cursor = conn.cursor()
    
    try:
        # 1. Recolección de datos GENERALES (Comunes a ambos tipos)
        data = request.form
        id_tipo_cliente = int(data.get('id_tipo_cliente'))
        nombre_cliente = data.get('nombre_cliente')
        apellido_cliente = data.get('apellido_cliente')
        direccion = data.get('direccion')
        telefono_cliente = data.get('telefono_cliente')
        email = data.get('email')

        # 2. INSERCIÓN EN LA TABLA CLIENTE (Cabecera)
        sql_cliente = """
            INSERT INTO cliente (id_tipo_cliente, nombre_cliente, apellido_cliente, direccion, telefono_cliente, email)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql_cliente, (id_tipo_cliente, nombre_cliente, apellido_cliente, direccion, telefono_cliente, email))
        
        # Obtener el ID recién insertado (CRUCIAL para la especialización, evita el error 1364)
        id_cliente_insertado = cursor.lastrowid 
        # Si usa mysql.connector y la clave primaria es AUTO_INCREMENT, 'lastrowid' es el método preferido.
        # Alternativamente, si usa la función get_last_insert_id() que se definió en db_config:
        # from db_config import get_db_connection, get_last_insert_id
        # id_cliente_insertado = get_last_insert_id(cursor)
        
        if id_cliente_insertado is None:
            raise Exception("No se pudo obtener el ID del cliente insertado. La inserción en la tabla 'cliente' falló.")

        # 3. INSERCIÓN CONDICIONAL (Especialización)
        mensaje = ""
        
        if id_tipo_cliente == 1:
            # Cliente Natural
            cedula_dni = data.get('cedula_dni')
            sql_natural = "INSERT INTO cliente_natural (id_cliente, cedula_dni) VALUES (%s, %s)"
            cursor.execute(sql_natural, (id_cliente_insertado, cedula_dni))
            mensaje = f"Cliente Natural '{nombre_cliente} {apellido_cliente}' registrado con éxito en SOLUCIONARTE."
            
        elif id_tipo_cliente == 2:
            # Cliente Jurídico
            rif_empresa = data.get('rif_empresa')
            nombre_empresa = data.get('nombre_empresa')
            cedula_dni_representante = data.get('cedula_dni_representante')
            
            sql_juridico = """
                INSERT INTO cliente_juridico (id_cliente, rif_empresa, nombre_empresa, cedula_dni_representante)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql_juridico, (id_cliente_insertado, rif_empresa, nombre_empresa, cedula_dni_representante))
            mensaje = f"Cliente Jurídico '{nombre_empresa}' registrado con éxito en SOLUCIONARTE."
        
        else:
             # Este caso no debería ocurrir si el formulario es correcto
             raise Exception("Tipo de cliente no válido.")
            
        # 4. Confirmar la Transacción (Aplica los cambios a la BD)
        conn.commit()
        return f"""
            <h1>✅ Éxito al registrar cliente</h1>
            <p>{mensaje}</p>
            <p>ID asignado: <b>{id_cliente_insertado}</b>. Verifique las tablas en Workbench.</p>
            <p><a href='/'>Volver al formulario</a></p>
        """

    except Exception as err:
        # Si algo falla (ej: campo obligatorio NULL, error de BD), revierte todo
        conn.rollback()
        # Se imprime el error completo en la consola del servidor para depuración
        print("Error en procesar_cliente:", err, file=sys.stderr)
        return f"""
            <h1>❌ Error al registrar cliente</h1>
            <p><b>Detalle:</b> {err}</p>
            <p>Asegúrese de que la conexión a MySQL esté activa y todos los campos requeridos estén llenos.</p>
            <p><a href='/'>Volver al formulario</a></p>
        """, 500
        
    finally:
        # Cierra el cursor y la conexión, asegurando que no queden recursos abiertos
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    # Asegúrate de que Flask esté en modo depuración (debug=True)
    app.run(debug=True)