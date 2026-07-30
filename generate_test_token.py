import os
import django
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dreamspharma.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from dreamspharmaapp.models import CustomUser

def generate_tokens():
    username = "9999999999"
    password = "Test@123456"
    
    user = CustomUser.objects.filter(username=username).first()
    if not user:
        user = CustomUser.objects.create_user(
            username=username,
            phone_number=username,
            password=password,
            role="RETAILER",
            status="APPROVED"
        )
        print(f"Created new retailer user: {username}")
    else:
        user.set_password(password)
        user.status = "APPROVED"
        user.save()
        print(f"Retrieved existing retailer user: {username}")
        
    # Generate tokens using simplejwt
    refresh = RefreshToken.for_user(user)
    
    print("\n" + "="*80)
    print("GENERATED JWT TOKENS")
    print("="*80)
    print(f"Access Token:\n{str(refresh.access_token)}\n")
    print(f"Refresh Token:\n{str(refresh)}")
    print("="*80)

if __name__ == '__main__':
    generate_tokens()
