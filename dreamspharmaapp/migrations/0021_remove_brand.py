# Generated migration to remove Brand model and brand field from ProductInfo

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dreamspharmaapp', '0020_customuser_profile_image'),
    ]

    operations = [
        # Remove the brand field from ProductInfo
        migrations.RemoveField(
            model_name='productinfo',
            name='brand',
        ),
        # Delete the Brand model
        migrations.DeleteModel(
            name='Brand',
        ),
    ]
