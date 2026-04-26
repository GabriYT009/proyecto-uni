from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_marca_producto_nombre_marca'),
    ]

    operations = [
        migrations.AddField(
            model_name='nota_entrega',
            name='cliente_direccion',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='nota_entrega',
            name='cliente_documento',
            field=models.CharField(blank=True, max_length=45, null=True),
        ),
        migrations.AddField(
            model_name='nota_entrega',
            name='cliente_nombre',
            field=models.CharField(blank=True, max_length=90, null=True),
        ),
        migrations.AddField(
            model_name='nota_entrega',
            name='cliente_telefono',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
