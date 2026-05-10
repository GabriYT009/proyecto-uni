from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_producto_codigo_producto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserCartSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cart', models.JSONField(blank=True, default=list)),
                ('cart_options', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=models.CASCADE, related_name='cart_snapshot', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Respaldo de carrito',
                'verbose_name_plural': 'Respaldos de carrito',
            },
        ),
    ]
