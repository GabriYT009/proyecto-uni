from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_usercartsnapshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='nota_entrega',
            name='descuento_monto',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='nota_entrega',
            name='descuento_motivo',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='nota_entrega',
            name='total_bruto',
            field=models.FloatField(blank=True, null=True),
        ),
    ]