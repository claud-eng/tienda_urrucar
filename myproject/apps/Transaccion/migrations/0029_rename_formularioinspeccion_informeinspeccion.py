# Generated by Django 4.2.10 on 2025-03-25 01:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0028_formularioinspeccion_alter_producto_imagen'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='FormularioInspeccion',
            new_name='InformeInspeccion',
        ),
    ]
