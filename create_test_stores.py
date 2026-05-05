import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
django.setup()

from dreamspharmaapp.models import Store

# Clean up first
Store.objects.all().delete()

# Create a store in Bangalore (e.g. Indiranagar)
Store.objects.create(
    name="DreamsPharma - Indiranagar",
    address="100 Feet Road, Indiranagar",
    city="Bangalore",
    state="Karnataka",
    pincode="560038",
    phone="9876543210",
    latitude=12.9784,
    longitude=77.6408,
    is_active=True,
    is_primary=True,
    erp_store_id="001",
    c2_code="03C000",
    prod_code="02"
)

# Create a store in Koramangala
Store.objects.create(
    name="DreamsPharma - Koramangala",
    address="80 Feet Road, Koramangala",
    city="Bangalore",
    state="Karnataka",
    pincode="560095",
    phone="9876543211",
    latitude=12.9352,
    longitude=77.6245,
    is_active=True,
    is_primary=False,
    erp_store_id="002",
    c2_code="03C001",
    prod_code="02"
)

# Create a store in Delhi
Store.objects.create(
    name="DreamsPharma - CP",
    address="Connaught Place",
    city="Delhi",
    state="Delhi",
    pincode="110001",
    phone="9876543212",
    latitude=28.6304,
    longitude=77.2177,
    is_active=True,
    is_primary=False,
    erp_store_id="003",
    c2_code="03C002",
    prod_code="02"
)

print("Stores created successfully.")
