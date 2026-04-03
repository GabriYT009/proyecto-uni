# Generated manually to support payment approval workflow.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='salida',
            name='comprobante_pago',
            field=models.ImageField(blank=True, null=True, upload_to='payment_proofs/'),
        ),
        migrations.AddField(
            model_name='salida',
            name='estado_pago',
            field=models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')], default='pendiente', max_length=20),
        ),
        migrations.AddField(
            model_name='salida',
            name='fecha_revision',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='salida',
            name='revisado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='salidas_revisadas', to='auth.user'),
        ),
    ]