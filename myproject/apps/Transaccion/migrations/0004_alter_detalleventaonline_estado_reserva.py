# Generated by Django 4.2.10 on 2024-12-10 23:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0003_detalleventaonline_estado_reserva'),
    ]

    operations = [
        migrations.AlterField(
            model_name='detalleventaonline',
            name='estado_reserva',
            field=models.CharField(blank=True, choices=[('En proceso', 'En proceso'), ('Vendida', 'Vendida'), ('Desistida', 'Desistida')], max_length=20, null=True),
        ),
    ]
