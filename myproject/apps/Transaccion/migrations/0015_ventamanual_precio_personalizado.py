# Generated by Django 4.2.10 on 2025-01-16 22:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0014_producto_costo_extra_producto_precio_costo'),
    ]

    operations = [
        migrations.AddField(
            model_name='ventamanual',
            name='precio_personalizado',
            field=models.PositiveIntegerField(blank=True, help_text='Precio personalizado si no se usa el precio de los servicios.', null=True),
        ),
    ]
