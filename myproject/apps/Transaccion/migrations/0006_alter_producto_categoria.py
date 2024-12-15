# Generated by Django 4.2.10 on 2024-12-11 04:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0005_alter_producto_categoria'),
    ]

    operations = [
        migrations.AlterField(
            model_name='producto',
            name='categoria',
            field=models.CharField(choices=[('Vehículo', 'Vehículo'), ('Otro', 'Otro'), ('Sin categoría', 'Sin categoría')], default='Sin categoría', max_length=100),
        ),
    ]