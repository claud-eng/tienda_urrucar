# Generated by Django 4.2.10 on 2025-03-05 06:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0026_presupuesto'),
    ]

    operations = [
        migrations.AddField(
            model_name='ventaonline',
            name='tbk_token',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
