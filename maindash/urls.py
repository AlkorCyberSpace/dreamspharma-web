from django.urls import path
from . import views

urlpatterns = [
    # SuperAdmin - Dashboard Statistics
    path('superadmin/dashboard/statistics/', views.DashboardStatisticsView.as_view(), name='superadmin-dashboard-statistics'),
    
    # SuperAdmin - Change Password
    path('superadmin/change-password/', views.ChangePasswordView.as_view(), name='superadmin-change-password'),
    
    # SuperAdmin - Get Profile Information
    path('superadmin/profile/', views.GetSuperAdminProfileView.as_view(), name='superadmin-get-profile'),
    
    # SuperAdmin - Profile Image (Upload/Delete)
    path('superadmin/profile/image/', views.ProfileImageView.as_view(), name='superadmin-profile-image'),
    
    # SuperAdmin - Get all retailers KYC and registration details
    path('superadmin/retailers/', views.SuperAdminGetAllRetailersView.as_view(), name='superadmin-get-all-retailers'),
    
    # SuperAdmin - Approve KYC by user_id
    path('superadmin/kyc/approve/<int:user_id>/', views.ApproveKYCView.as_view(), name='superadmin-approve-kyc'),
    
    # SuperAdmin - Reject KYC by user_id
    path('superadmin/kyc/reject/<int:user_id>/', views.RejectKYCView.as_view(), name='superadmin-reject-kyc'),
    
    # SuperAdmin - Logout
    path('superadmin/logout/', views.SuperAdminLogoutView.as_view(), name='superadmin-logout'),
    
    # SuperAdmin - Add Category/Brand
    path('superadmin/add-category/', views.AddCategoryView.as_view(), name='superadmin-add-category'),
    path('superadmin/add-category/<int:category_id>/', views.AddCategoryView.as_view(), name='superadmin-add-category-detail'),
    
    # SuperAdmin - Assign Brand to Product
    path('superadmin/assign-brand/', views.AssignBrandToProductView.as_view(), name='superadmin-assign-brand'),


    # ==================== OFFERS & BANNERS ENDPOINTS ====================
    # Offers Management (SuperAdmin)
    path('offers/', views.OfferListCreateView.as_view(), name='offer-list-create'),
    path('offers/<str:offer_id>/', views.OfferDetailView.as_view(), name='offer-detail'),
    
    # Public Endpoints - Homepage & Category Offers
    path('offers/homepage/', views.HomePageOffersView.as_view(), name='homepage-offers'),
    path('offers/category/<int:category_id>/', views.CategoryOffersView.as_view(), name='category-offers'),
]
   