# Generated by Django 4.2.10 on 2025-01-20 22:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0015_ventamanual_precio_personalizado'),
    ]

    operations = [
        migrations.AddField(
            model_name='detalleventaonline',
            name='dias_desde_adquisicion',
            field=models.PositiveIntegerField(blank=True, help_text='Días transcurridos desde la adquisición del producto', null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='fecha_adquisicion',
            field=models.DateField(blank=True, help_text='Fecha en que se adquirió el producto', null=True),
        ),
    ]
