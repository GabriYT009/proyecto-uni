import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_salida_pago_revision'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='carritodecompras',
            options={},
        ),
        # Le decimos a Django que asuma que usuario ya se borró, sin ejecutar el SQL
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveField(
                    model_name='carritodecompras',
                    name='usuario',
                ),
            ],
            database_operations=[],
        ),
        # Le decimos a Django que asuma que Cantidad ya se creó, sin intentar duplicarla
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='carritodecompras',
                    name='Cantidad',
                    field=models.PositiveIntegerField(default=1),
                ),
            ],
            database_operations=[],
        ),
        migrations.AddField(
            model_name='carritodecompras',
            name='Producto',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='core.producto'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='carritodecompras',
            name='precio_unitario',
            field=models.DecimalField(decimal_places=2, default=1, max_digits=10),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Nota_Entrega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_pago', models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('APROBADO', 'Aprobado'), ('RECHAZADO', 'Rechazado')], default='PENDIENTE', max_length=20)),
                ('fecha_revision', models.DateTimeField(blank=True, null=True)),
                ('total', models.FloatField(blank=True, null=True)),
                ('fecha', models.DateTimeField(blank=True, null=True)),
                ('bcv', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.bcv')),
                ('carrito_de_compras', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.carritodecompras')),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='core.cliente')),
                ('metodo_pago', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='core.metodopago')),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='Nota_Entrega_revisadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Nota_Entrega (Venta)',
                'verbose_name_plural': 'Nota_Entrega',
            },
        ),
        migrations.AddField(
            model_name='carritodecompras',
            name='Nota_Entrega',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='core.nota_entrega'),
            preserve_default=False,
        ),
        migrations.DeleteModel(
            name='Salida',
        ),
    ]