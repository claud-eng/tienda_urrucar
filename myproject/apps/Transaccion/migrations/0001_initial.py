# Generated by Django 4.2.10 on 2024-11-10 21:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('Usuario', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContenidoCarrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='DetalleVentaOnline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cantidad', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Producto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('marca', models.CharField(max_length=100)),
                ('categoria', models.CharField(max_length=100, null=True)),
                ('descripcion', models.TextField()),
                ('precio', models.PositiveIntegerField()),
                ('cantidad_stock', models.PositiveIntegerField()),
                ('imagen', models.ImageField(blank=True, null=True, upload_to='productos/')),
            ],
        ),
        migrations.CreateModel(
            name='Servicio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField()),
                ('precio', models.PositiveIntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='VentaOnline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('estado', models.CharField(default='pendiente', max_length=20)),
                ('token_ws', models.CharField(blank=True, max_length=100, null=True)),
                ('numero_orden', models.CharField(blank=True, max_length=26, null=True)),
                ('tipo_pago', models.CharField(blank=True, max_length=30, null=True)),
                ('monto_cuotas', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('numero_cuotas', models.PositiveIntegerField(blank=True, null=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Usuario.cliente')),
                ('productos', models.ManyToManyField(through='Transaccion.DetalleVentaOnline', to='Transaccion.producto')),
                ('servicios', models.ManyToManyField(through='Transaccion.DetalleVentaOnline', to='Transaccion.servicio')),
            ],
        ),
        migrations.CreateModel(
            name='VentaManual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('total', models.PositiveIntegerField(default=0)),
                ('pago_cliente', models.PositiveIntegerField(default=0)),
                ('cambio', models.PositiveIntegerField(default=0)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Usuario.cliente')),
            ],
        ),
        migrations.AddField(
            model_name='detalleventaonline',
            name='orden_compra',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Transaccion.ventaonline'),
        ),
        migrations.AddField(
            model_name='detalleventaonline',
            name='producto',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Transaccion.producto'),
        ),
        migrations.AddField(
            model_name='detalleventaonline',
            name='servicio',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Transaccion.servicio'),
        ),
        migrations.CreateModel(
            name='DetalleVentaManual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.PositiveIntegerField(default=1)),
                ('subtotal', models.PositiveIntegerField(default=0)),
                ('orden_venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalleventamanual_set', to='Transaccion.ventamanual')),
                ('producto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Transaccion.producto')),
                ('servicio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Transaccion.servicio')),
            ],
        ),
        migrations.CreateModel(
            name='Carrito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('cantidad', models.PositiveIntegerField()),
                ('carrito', models.PositiveIntegerField(default=1)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Usuario.cliente')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
    ]
