"""Insertar una nota de reembolso de prueba en la base de datos activa.

Este script usa la configuración de Django y funciona con la DB de Railway
cuando el entorno tiene DATABASE_URL / MYSQL_URL configurado.

Ejecutar desde backend/:
    python scripts/insert_prueba_reembolso.py

Si prefieres usar PowerShell con el venv:
    cd c:/Users/eduar/Desktop/pantalla/backend
    .venv\Scripts\Activate.ps1
    python scripts/insert_prueba_reembolso.py
"""

import os
import django
from django.utils import timezone
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()

TABLE_NAME = 'core_nota_entrega'

REJECTED_NOTE = {
    'estado_pago': 'RECHAZADO',
    'fecha': timezone.now(),
    'total': 150.0,
    'motivo_rechazo': 'Prueba de reembolso generada desde script',
    'cliente_nombre': 'Cliente Prueba'
}


def get_table_columns(table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
        columns = []
        for row in description:
            if hasattr(row, 'name'):
                columns.append(row.name)
            else:
                columns.append(row[0])
        return [col.lower() for col in columns]


def quote_name(name):
    return connection.ops.quote_name(name)


def insert_rejected_note():
    columns = get_table_columns(TABLE_NAME)
    if not columns:
        raise RuntimeError(f'No se encontró la tabla {TABLE_NAME} en la base de datos activa.')

    cliente_column = None
    if 'cliente_cedula' in columns:
        cliente_column = 'cliente_cedula'
    elif 'cliente_id' in columns:
        cliente_column = 'cliente_id'

    fields = ['estado_pago', 'fecha', 'total', 'motivo_rechazo', 'cliente_nombre']
    values = [REJECTED_NOTE[field] for field in fields]

    if cliente_column and cliente_column not in fields:
        fields.append(cliente_column)
        values.append(None)

    quoted_fields = ', '.join(quote_name(field) for field in fields)
    placeholders = ', '.join('%s' for _ in fields)

    sql = f'INSERT INTO {quote_name(TABLE_NAME)} ({quoted_fields}) VALUES ({placeholders})'

    with connection.cursor() as cursor:
        cursor.execute(sql, values)
        inserted_id = cursor.lastrowid
    connection.commit()
    return inserted_id


def count_rejected_notes():
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {quote_name(TABLE_NAME)} WHERE {quote_name('estado_pago')} = %s",
            ['RECHAZADO']
        )
        return cursor.fetchone()[0]


if __name__ == '__main__':
    print('Insertando nota de reembolso de prueba...')
    try:
        inserted_id = insert_rejected_note()
        total = count_rejected_notes()
        print(f'Nota insertada con id={inserted_id}')
        print(f'Total notas rechazadas en base: {total}')
    except Exception as exc:
        print('Error al insertar la nota de reembolso de prueba:')
        raise
