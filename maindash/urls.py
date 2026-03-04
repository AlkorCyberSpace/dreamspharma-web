from django.urls import path
from . import views

urlpatterns = [
    # SuperAdmin - Get all retailers KYC and registration details
    path('superadmin/retailers/', views.SuperAdminGetAllRetailersView.as_view(), name='superadmin-get-all-retailers'),
    
    # SuperAdmin - Approve KYC by user_id
    path('superadmin/kyc/approve/<int:user_id>/', views.ApproveKYCView.as_view(), name='superadmin-approve-kyc'),
    
    # SuperAdmin - Reject KYC by user_id
    path('superadmin/kyc/reject/<int:user_id>/', views.RejectKYCView.as_view(), name='superadmin-reject-kyc'),
]
