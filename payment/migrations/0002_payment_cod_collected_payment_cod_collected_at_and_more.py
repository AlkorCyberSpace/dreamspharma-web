

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [

        ('payment', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='cod_collected',
            field=models.BooleanField(default=False, help_text='For COD orders, marks if cash has been collected'),
        ),
        migrations.AddField(
            model_name='payment',
            name='cod_collected_at',
            field=models.DateTimeField(blank=True, help_text='Timestamp when COD payment was collected', null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='cod_collected_by',
            field=models.CharField(blank=True, help_text='Name/ID of person who collected COD', max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(choices=[('RAZORPAY', 'Razorpay'), ('NETBANKING', 'Net Banking'), ('WALLET', 'Wallet'), ('UPI', 'UPI'), ('COD', 'Cash on Delivery')], default='RAZORPAY', max_length=20),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['payment_method', 'status'], name='payment_pay_payment_c42eba_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['cod_collected', '-cod_collected_at'], name='payment_pay_cod_col_e9e17d_idx'),
        ),
    ]
