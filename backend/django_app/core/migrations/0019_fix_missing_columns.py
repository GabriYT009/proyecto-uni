from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_remove_cliente_rif_empresarial'), # La anterior que está fallando
    ]

    operations = [
        # Esto hace que Django "ignore" el intento de borrar columnas que ya no existen
        migrations.RunSQL(
            sql="SELECT 1;", 
            reverse_sql="SELECT 1;"
        )
    ]