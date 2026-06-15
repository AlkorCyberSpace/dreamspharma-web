# Generated migration for wallet intent tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dreamspharmaapp', '0037_alter_cart_platform_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesorder',
            name='wallet_requested',
            field=models.BooleanField(
                default=False,
                help_text='Whether customer requested to use wallet for this order'
            ),
        ),
        migrations.AddField(
            model_name='salesorder',
            name='wallet_intent_user_id',
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                help_text='User ID of wallet owner (for wallet deduction after payment succeeds)'
            ),
        ),
        migrations.AddField(
            model_name='salesorder',
            name='wallet_applied_amount',
            field=models.DecimalField(
                max_digits=12,
                decimal_places=2,
                default=0.00,
                help_text='Amount actually deducted from wallet (zero until payment succeeds)'
            ),
        ),
        migrations.AddField(
            model_name='salesorder',
            name='wallet_applied_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When wallet was applied (only after payment succeeds)'
            ),
        ),
    ]
