import os

with open('/tmp/cod_code.py', 'r') as f:
    cod_code = f.read()
    
with open('/tmp/reports_code.py', 'r') as f:
    reports_code = f.read()

urls_code = """
from django.urls import path
from . import views

urlpatterns = [
    # ... other admin urls

    # COD DELIVERY STATUS
    path('superadmin/orders/<str:order_id>/cod-delivered/', views.SuperAdminMarkCODDeliveredView.as_view(), name='superadmin-mark-cod-delivered'),

    # REPORTS
    path('superadmin/reports/summary/', views.ReportSummaryView.as_view(), name='superadmin-report-summary'),
    path('superadmin/reports/kyc/', views.KYCStatusReportView.as_view(), name='superadmin-report-kyc'),
    path('superadmin/reports/orders/', views.OrderReportView.as_view(), name='superadmin-report-orders'),
    path('superadmin/reports/retailer-activity/', views.RetailerActivityReportView.as_view(), name='superadmin-report-retailer-activity'),
    path('superadmin/reports/revenue/', views.RevenueReportView.as_view(), name='superadmin-report-revenue'),
]
"""

content = f"""# Backend Export: Reports & COD Delivery

Here is all the relevant code for the Admin Reports and Cash On Delivery verification APIs. You can copy and paste this into the views and urls of the other system.

### URLs (`urls.py`)
```python
{urls_code.strip()}
```

### Views (`views.py`)

#### 1. Cash on Delivery Verification View
```python
{cod_code.strip()}
```

#### 2. Admin Reports API Views
```python
import openpyxl
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q, Avg, Max
from django.utils.dateparse import parse_date

{reports_code.strip()}
```
"""

os.makedirs('/Users/sreejith/.gemini/antigravity/artifacts', exist_ok=True)
with open('/Users/sreejith/.gemini/antigravity/artifacts/reports_and_cod.md', 'w') as f:
    f.write(content)

