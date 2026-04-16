import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from dreamspharmaapp.models import SalesOrder, Address
from payment.models import Payment
from django.utils import timezone

User = get_user_model()

print("===========================================")
print("  COD DELIVERY API TEST SCRIPT")
print("===========================================\n")

# 1. Setup Admin User
admin_user, created = User.objects.get_or_create(
    username='test_cod_admin',
    email='cod_admin@test.com',
    defaults={'role': 'SUPERADMIN', 'is_superuser': True}
)
if created or not admin_user.check_password('password123'):
    admin_user.set_password('password123')
    admin_user.role = 'SUPERADMIN'
    admin_user.is_superuser = True
    admin_user.save()

# 2. Setup Retailer User
retailer, created = User.objects.get_or_create(
    username='test_retailer_cod',
    phone_number='9998887776',
    defaults={'role': 'RETAILER'}
)

# 3. Create a Test Address
address, _ = Address.objects.get_or_create(
    user=retailer,
    name='Retailer Address',
    phone='9998887776',
    pincode='123456',
    city='Test City',
    state='Test State',
    locality='Test Locality'
)

# 4. Create a SalesOrder
order_id = 'ORD-TEST-COD-001'
SalesOrder.objects.filter(order_id=order_id).delete()
order = SalesOrder.objects.create(
    order_id=order_id,
    patient_name='Test Patient',
    delivery_address=address,
    ord_date=timezone.now().date(),
    order_total=150.00,
    store_id='RET001'
)

# 5. Create a COD Payment
Payment.objects.create(
    user=retailer,
    sales_order=order,
    amount=150.00,
    payment_method='COD',
    status='PENDING',
    customer_name='Test Patient',
    customer_email='test@example.com',
    customer_phone='9998887776'
)

print("[INFO] Setup complete: Created order with ID:", order_id)

client = APIClient()

print("\n1. [ACTION] Triggering SuperAdmin Login via API...")
response = client.post('/api/auth/login/', {'username': 'test_cod_admin', 'password': 'password123'}, format='json')
if response.status_code == 200:
    print("   [+] Success! Login successful & token received.")
    token = response.data['access']
else:
    print(f"   [-] Failed! Status: {response.status_code}")
    exit(1)

client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

print("\n2. [ACTION] Hitting COD Delivery Endpoint...")
response = client.post(f'/api/superadmin/orders/{order_id}/cod-delivered/')

if response.status_code == 200:
    print("   [+] Success! Status Code 200 OK")
    print("   [+] Response:", response.data)
else:
    print(f"   [-] Failed! Status: {response.status_code}")
    print("   [-] Response:", response.data)
    exit(1)

print("\n3. [VERIFY] Checking Database directly...")
order.refresh_from_db()
payment = order.payments.first()

print(f"   Order dc_conversion_flag (Delivered): {order.dc_conversion_flag}")
print(f"   Payment status: {payment.status}")
print(f"   Payment cod_collected: {payment.cod_collected}")

if order.dc_conversion_flag and payment.status == 'SUCCESS' and payment.cod_collected:
    print("\n===========================================")
    print("  TEST PASSED SUCCESSFULLY ✅")
    print("===========================================\n")
else:
    print("\n===========================================")
    print("  TEST FAILED ❌")
    print("===========================================\n")
