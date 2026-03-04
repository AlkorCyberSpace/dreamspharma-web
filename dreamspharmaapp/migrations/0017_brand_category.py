# Generated migration for Brand and ProductInfo models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dreamspharmaapp', '0016_apitoken_invoice_itemmaster_salesorder_cart_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='brands/')),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ProductInfo',
            fields=[
                ('item', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name='product_info', serialize=False, to='dreamspharmaapp.itemmaster')),
                ('description', models.TextField(blank=True, null=True)),
                ('product_image', models.ImageField(blank=True, null=True, upload_to='products/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('brand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='dreamspharmaapp.brand')),
            ],
            options={
                'verbose_name_plural': 'Product Info',
                'ordering': ['-created_at'],
            },
        ),
    ]
