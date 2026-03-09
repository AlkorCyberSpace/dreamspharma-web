from django.urls import path
from . import views

urlpatterns = [
    # SuperAdmin - Dashboard Statistics
    path('superadmin/dashboard/statistics/', views.DashboardStatisticsView.as_view(), name='superadmin-dashboard-statistics'),
    
    # SuperAdmin - Change Password
    path('superadmin/change-password/', views.ChangePasswordView.as_view(), name='superadmin-change-password'),
    
    # SuperAdmin - Get Profile Information
    path('superadmin/profile/', views.GetSuperAdminProfileView.as_view(), name='superadmin-get-profile'),
    
    # SuperAdmin - Upload Profile Image
    path('superadmin/profile/image/', views.UploadSuperAdminProfileImageView.as_view(), name='superadmin-upload-profile-image'),
    
    # SuperAdmin - Delete Profile Image
    path('superadmin/profile/image/', views.DeleteSuperAdminProfileImageView.as_view(), name='superadmin-delete-profile-image'),
    
    # SuperAdmin - Get all retailers KYC and registration details
    path('superadmin/retailers/', views.SuperAdminGetAllRetailersView.as_view(), name='superadmin-get-all-retailers'),
    
    # SuperAdmin - Approve KYC by user_id
    path('superadmin/kyc/approve/<int:user_id>/', views.ApproveKYCView.as_view(), name='superadmin-approve-kyc'),
    
    # SuperAdmin - Reject KYC by user_id
    path('superadmin/kyc/reject/<int:user_id>/', views.RejectKYCView.as_view(), name='superadmin-reject-kyc'),
    
    # SuperAdmin - Logout
    path('superadmin/logout/', views.SuperAdminLogoutView.as_view(), name='superadmin-logout'),
]
