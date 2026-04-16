from django.urls import path
from . import views

urlpatterns = [
    # SuperAdmin - Dashboard Statistics
    path('superadmin/dashboard/statistics/', views.DashboardStatisticsView.as_view(), name='superadmin-dashboard-statistics'),
    path('superadmin/dashboard/daily-volume/', views.DailyVolumeGraphView.as_view(), name='superadmin-daily-volume'),

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

    # ==================== AUDIT LOGS ====================
    path('superadmin/audit-logs/', views.AuditLogListView.as_view(), name='superadmin-audit-logs'),

    # ==================== ORDER MANAGEMENT ====================
    path('superadmin/orders/', views.SuperAdminOrdersView.as_view(), name='superadmin-orders'),
    path('superadmin/orders/<str:order_id>/cod-delivered/', views.SuperAdminMarkCODDeliveredView.as_view(), name='superadmin-mark-cod-delivered'),

    # ==================== OFFERS & BANNERS ENDPOINTS ====================
    # Offers Management (SuperAdmin)
    path('offers/', views.OfferListCreateView.as_view(), name='offer-list-create'),
    path('offers/<str:offer_id>/', views.OfferDetailView.as_view(), name='offer-detail'),

    # Public Endpoints - Homepage & Category Offers
    path('offers/homepage/', views.HomePageOffersView.as_view(), name='homepage-offers'),
    path('offers/category/<int:category_id>/', views.CategoryOffersView.as_view(), name='category-offers'),
    # ==================== ADMIN NOTIFICATIONS ENDPOINTS ====================
    # SuperAdmin - Notifications
    path('superadmin/notifications/', views.AdminNotificationListView.as_view(), name='superadmin-notifications'),
    path('superadmin/notifications/<int:notification_id>/mark-read/', views.AdminNotificationMarkReadView.as_view(), name='superadmin-notification-mark-read'),

    # ==================== REPORTS & ANALYTICS ====================
    path('superadmin/reports/summary/', views.ReportSummaryView.as_view(), name='superadmin-report-summary'),
    path('superadmin/reports/kyc/', views.KYCStatusReportView.as_view(), name='superadmin-report-kyc'),
    path('superadmin/reports/orders/', views.OrderReportView.as_view(), name='superadmin-report-orders'),
    path('superadmin/reports/retailer-activity/', views.RetailerActivityReportView.as_view(), name='superadmin-report-retailer-activity'),
    path('superadmin/reports/revenue/', views.RevenueReportView.as_view(), name='superadmin-report-revenue'),
]
   
