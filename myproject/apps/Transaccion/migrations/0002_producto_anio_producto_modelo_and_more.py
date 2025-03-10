# Generated by Django 4.2.10 on 2024-12-09 20:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Transaccion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='anio',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='modelo',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_reserva',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='version',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
