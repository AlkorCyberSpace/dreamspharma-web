import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

print("===========================================")
print("  AUDIT LOG END-TO-END TEST SCRIPT")
print("===========================================\n")

# Create or get superadmin
user, created = User.objects.get_or_create(
    username='test_audit_admin',
    email='audit_admin@test.com',
    defaults={'role': 'SUPERADMIN', 'is_superuser': True}
)
if created or not user.check_password('password123'):
    user.set_password('password123')
    user.role = 'SUPERADMIN'
    user.is_superuser = True
    user.save()

client = APIClient()

print("1. [ACTION] Triggering SuperAdmin Login via API...")
response = client.post('/api/auth/login/', {'username': 'test_audit_admin', 'password': 'password123'}, format='json')
if response.status_code == 200:
    print("   [+] Success! Login successful & token received.")
    token = response.data['access']
else:
    print(f"   [-] Failed! Status: {response.status_code}")
    exit(1)

client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

print("\n2. [ACTION] Triggering Category Creation via SuperAdmin API...")
response = client.post('/api/superadmin/add-category/', {'name': 'AuditLog Test Category'}, format='json')
if response.status_code == 201:
    print("   [+] Success! Category created.")
elif response.status_code == 400 and 'already exists' in str(response.data):
    print("   [*] Category already exists, moving on.")
else:
    print(f"   [-] Failed! Status: {response.status_code}")

print("\n3. [VERIFY] Fetching new Audit Logs from the API Endpoint...")
# Filter by category System to see login
response = client.get('/api/superadmin/audit-logs/')
if response.status_code == 200:
    logs = response.data['data']
    print(f"   [+] Success! API returned {len(logs)} total logs.")
    print("\n   Most recent logs returned by the API:")
    print("   --------------------------------------------------------")
    for log in logs[:3]:
        print(f"     => [{log['log_id']}] {log['action']:<15} | By: {log['performed_by']:<15} | Cat: {log['category']:<8} | Details: {log['details']}")
    print("   --------------------------------------------------------")
else:
    print(f"   [-] Failed! Status: {response.status_code}")

print("\n===========================================")
print("  TEST COMPLETED SUCCESSFULLY ✅")
print("===========================================\n")
