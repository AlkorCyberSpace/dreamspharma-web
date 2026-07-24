# Related Products endpoint
from django.urls import path
from .views import related_products
from django.urls import path
from . import views
from .store_views import (
    find_nearest_store,
    find_nearby_stores,
    get_store_details,
    get_store_erp_config,
    StoreViewSet,
    AdminStoreViewSet
)
from .notification_views import (
    RetailerNotificationsListView,
    RetailerNotificationDetailView,
    RetailerNotificationCountView
)
from .invoice_views import InvoiceDownloadView


urlpatterns = [
    # ==================== STORE ENDPOINTS ====================
    # Admin Store / Warehouse CRUD
    path('admin/warehouses/', AdminStoreViewSet.as_view({'get': 'list', 'post': 'create'}), name='admin-warehouses-list'),
    path('admin/warehouses/<int:pk>/', AdminStoreViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='admin-warehouses-detail'),

    path('stores/', StoreViewSet.as_view({'get': 'list'}), name='stores-list'),
    path('stores/<int:pk>/', StoreViewSet.as_view({'get': 'retrieve'}), name='stores-detail'),
    path('stores/find-nearest/', find_nearest_store, name='find-nearest-store'),
    path('stores/find-nearby/', find_nearby_stores, name='find-nearby-stores'),
    path('stores/<int:store_id>/details/', get_store_details, name='store-details'),
    path('stores/<int:store_id>/erp-config/', get_store_erp_config, name='store-erp-config'),
    
    # SuperAdmin Authentication
    path('auth/login/', views.SuperAdminLoginView.as_view(), name='superadmin-login'),
    # Retailer Authentication
    path('retailer-auth/login/', views.RetailerLoginView.as_view(), name='retailer-login'),
    path('retailer-auth/verify-otp/', views.RetailerVerifyOTPView.as_view(), name='retailer-verify-otp'),
    path('retailer-auth/resend-otp/', views.RetailerResendOTPView.as_view(), name='retailer-resend-otp'),
    path('retailer-auth/token/refresh/', views.TokenRefreshView.as_view(), name='token-refresh'),  # Silent token refresh
    # User Registration
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
    # Logout
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    # OTP Management
    path('otp/request_otp/', views.OTPRequestView.as_view(), name='otp-request'),
    path('otp/verify_otp/', views.OTPVerifyView.as_view(), name='otp-verify'),
    # Forgot Password & Reset
    path('auth/forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/verify-reset-otp/', views.ResetOTPVerifyView.as_view(), name='verify-reset-otp'),
    path('auth/reset-password/', views.PasswordResetView.as_view(), name='reset-password'),
    # KYC Management
    path('kyc/submit/<int:user_id>/', views.KYCSubmitView.as_view(), name='kyc-submit'),
    path('kyc/status/', views.KYCStatusView.as_view(), name='kyc-status'),
    # Home
    path('home/', views.HomeView.as_view(), name='home'),
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    # Change Password
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('auth/superadmin-change-password/', views.SuperAdminChangePasswordView.as_view(), name='superadmin-change-password'),
    
    # ==================== ERP INTEGRATION ENDPOINTS ====================
    path('erp/ws_c2_services_generate_token', views.GenerateTokenView.as_view(), name='generate-token'),
    # Item Masters (Token-based - user extracted from JWT)
    path('erp/ws_c2_services_get_master_data', views.GetItemMasterView.as_view(), name='get-item-master'),
    # Product Info Update
    path('erp/update_product_info/', views.UpdateProductInfoView.as_view(), name='update-product-info'),
    path('erp/upload_product_image/', views.UploadProductImageView.as_view(), name='upload-product-image'),
    # Stock Fetch
    path('erp/ws_c2_services_fetch_stock', views.FetchStockView.as_view(), name='fetch-stock'),
    # Sales Order Creation
    path('erp/ws_c2_services_create_sale_order', views.CreateSalesOrderView.as_view(), name='create-sales-order'),
    # Customer Creation
    path('erp/ws_c2_services_gl_cust_creation', views.CreateGLCustomerView.as_view(), name='create-gl-customer'),
    # Order Status
    path('erp/ws_c2_services_get_orderstatus', views.GetOrderStatusView.as_view(), name='get-order-status'),
    # ERP Redis Cache Management (SuperAdmin only)
    path('erp/cache/invalidate/', views.ERPCacheInvalidateView.as_view(), name='erp-cache-invalidate'),
    path('erp/cache/info/', views.ERPCacheInfoView.as_view(), name='erp-cache-info'),

    # ==================== CART ENDPOINTS ====================
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('cart/item/<int:item_id>/', views.UpdateCartItemView.as_view(), name='update-cart-item'),
    
    # ==================== ORDERS ENDPOINTS ====================
    path('orders/', views.RetailerOrdersView.as_view(), name='retailer-orders'),
    
    # ==================== WISHLIST ENDPOINTS ====================
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/add/', views.AddToWishlistView.as_view(), name='add-to-wishlist'),
    path('wishlist/item/<int:item_id>/', views.RemoveFromWishlistView.as_view(), name='remove-from-wishlist'),
    path('wishlist/item/<int:item_id>/update/', views.UpdateWishlistItemView.as_view(), name='update-wishlist-item'),
    path('wishlist/move-to-cart/', views.MoveToCartView.as_view(), name='move-to-cart'),
    
    # ==================== ADDRESS ENDPOINTS ====================
    path('address/', views.ListAddressesView.as_view(), name='list-addresses'),
    path('address/create/', views.CreateAddressView.as_view(), name='create-address'),
    path('address/<int:address_id>/', views.UpdateAddressView.as_view(), name='update-address'),
    path('address/<int:address_id>/delete/', views.DeleteAddressView.as_view(), name='delete-address'),
    path('address/<int:address_id>/default/', views.SetDefaultAddressView.as_view(), name='set-default-address'),
    path('checkout/preview/', views.OrderConfirmationPreviewView.as_view(), name='checkout-preview'),
    path('checkout/address/', views.CheckoutWithAddressView.as_view(), name='checkout-with-address'),
    
    # ==================== NOTIFICATIONS ENDPOINTS ====================
    path('notifications/register/<int:user_id>/', views.RegisterDeviceTokenView.as_view(), name='register-device-token'),
    path('notifications/register/', views.RegisterDeviceTokenView.as_view(), name='register-device-token-no-user'),
    
    # ==================== GPS LOCATION DETECTION ENDPOINTS ====================
    path('location/detect/<int:user_id>/', views.DetectCurrentLocationView.as_view(), name='detect-location'),
    path('location/confirm-address/<int:user_id>/', views.ConfirmLocationAddressView.as_view(), name='confirm-location-address'),
    path('location/nearby-addresses/<int:user_id>/', views.NearbyAddressesView.as_view(), name='nearby-addresses'),
    
    # ==================== PRODUCT ENDPOINTS ====================
    path('products/', views.AllProductsView.as_view(), name='all-products'),
    path('search/', views.SearchProductsView.as_view(), name='search-products'),
    path('search/popular/', views.PopularSearchView.as_view(), name='popular-search'),
    path('search/log/', views.LogSearchView.as_view(), name='log-search'),
    
    # ==================== RECOMMENDATION ENDPOINTS ====================
    path('recommendations/for-you/', views.PersonalizedRecommendationsView.as_view(), name='personalized-recommendations'),
    path('recommendations/frequently-bought/', views.FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('recommendations/top-selling/', views.TopSellingProductsView.as_view(), name='top-selling-products'),
    path('recommendations/popular/', views.PopularProductsView.as_view(), name='popular-products'),
    path('recommendations/recently-viewed/', views.RecentlyViewedView.as_view(), name='recently-viewed'),
    path('recommendations/user-activity/', views.UserRecentActivityView.as_view(), name='user-activity'),
    
    # Category List for Retailers
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:user_id>/', views.CategoryListView.as_view(), name='category-list-with-user'),

    # Related products (category-based, user-specific)
    path('products/<str:product_id>/related/', views.related_products, name='related-products'),
    path('orders/<str:order_id>/invoice/', InvoiceDownloadView.as_view(), name='download-invoice'),
    path('superadmin/orders/', views.SuperAdminOrdersView.as_view(), name='superadmin-orders'),
    
    # ==================== RETAILER NOTIFICATIONS ENDPOINTS ====================
    path('retailer-notifications/count/', RetailerNotificationCountView.as_view(), name='retailer-notification-count'),
    path('retailer-notifications/<str:notification_id>/', RetailerNotificationDetailView.as_view(), name='retailer-notification-detail'),
    path('retailer-notifications/', RetailerNotificationsListView.as_view(), name='retailer-notifications-list'),
    
    # ==================== CREDIT NOTE ENDPOINTS ====================
    # Retailer endpoints
    path('credit-notes/order-products/', views.GetProductsByOrderView.as_view(), name='credit-note-order-products'),
    path('credit-notes/create/', views.RetailerCreditNoteCreateView.as_view(), name='credit-note-create'),
    path('credit-notes/', views.RetailerCreditNoteListView.as_view(), name='credit-note-list'),
    
    # Admin endpoints
    path('admin/credit-notes/', views.AdminCreditNoteListView.as_view(), name='admin-credit-note-list'),
    path('admin/credit-notes/<str:credit_note_id>/', views.AdminCreditNoteDetailView.as_view(), name='admin-credit-note-detail'),
    path('admin/credit-notes/<str:credit_note_id>/approve/', views.AdminCreditNoteApproveView.as_view(), name='admin-credit-note-approve'),
    path('admin/credit-notes/<str:credit_note_id>/reject/', views.AdminCreditNoteRejectView.as_view(), name='admin-credit-note-reject'),
    
    # ==================== WALLET ENDPOINTS ====================
    # Wallet applied during sales order creation now - see CreateSalesOrderView
    # Legacy endpoint deprecated - use use_wallet parameter in /erp/ws_c2_services_create_sale_order
    path('wallet/', views.RetailerWalletView.as_view(), name='retailer-wallet'),
    path('wallet/apply/', views.ApplyWalletToOrderView.as_view(), name='apply-wallet-to-order'),

    # ==================== STARTUP LOCATION ENDPOINTS ====================
    #   POST /api/location/detect/           — Public. GPS coords → address + nearest store (anonymous)
    #   GET  /api/location/me/               — Authenticated. Retrieve last saved location for user
    #   POST /api/location/save/             — Authenticated. Explicitly update saved location for user
    path('location/detect/',              views.StartupDetectLocationView.as_view(), name='startup-location-detect'),
    path('location/me/',                  views.GetMyLocationView.as_view(),          name='get-my-location'),
    path('location/save/',                views.SaveMyLocationView.as_view(),         name='save-my-location'),
]
