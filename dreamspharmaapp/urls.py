# Related Products endpoint
from django.urls import path
from .views import related_products
from django.urls import path
from . import views

urlpatterns = [
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
    path('profile/<int:user_id>/', views.ProfileView.as_view(), name='profile-by-id'),
    # Change Password
    path('auth/change-password/<int:user_id>/', views.ChangePasswordView.as_view(), name='change-password'),
    path('auth/superadmin-change-password/', views.SuperAdminChangePasswordView.as_view(), name='superadmin-change-password'),
    
    # ==================== ERP INTEGRATION ENDPOINTS ====================
 
    path('erp/ws_c2_services_generate_token', views.GenerateTokenView.as_view(), name='generate-token'),
    # Item Masters
    path('erp/ws_c2_services_get_master_data/<int:user_id>/', views.GetItemMasterView.as_view(), name='get-item-master'),
    path('erp/ws_c2_services_get_master_data', views.GetItemMasterView.as_view(), name='get-item-master-no-user'),
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
    
    # ==================== CART ENDPOINTS ====================
    path('cart/<int:user_id>/', views.CartView.as_view(), name='cart'),
    path('cart/add/<int:user_id>/', views.AddToCartView.as_view(), name='add-to-cart'),
    path('cart/item/<int:item_id>/', views.UpdateCartItemView.as_view(), name='update-cart-item'),
    
    # ==================== WISHLIST ENDPOINTS ====================
    path('wishlist/', views.WishlistView.as_view(), name='wishlist'),
    path('wishlist/<int:user_id>/', views.WishlistView.as_view(), name='wishlist-by-user'),
    path('wishlist/add/<int:user_id>/', views.AddToWishlistView.as_view(), name='add-to-wishlist'),
    path('wishlist/item/<int:item_id>/', views.RemoveFromWishlistView.as_view(), name='remove-from-wishlist'),
    path('wishlist/item/<int:item_id>/update/', views.UpdateWishlistItemView.as_view(), name='update-wishlist-item'),
    path('wishlist/move-to-cart/', views.MoveToCartView.as_view(), name='move-to-cart'),
    
    # ==================== ADDRESS ENDPOINTS ====================
    path('address/<int:user_id>/', views.ListAddressesView.as_view(), name='list-addresses'),
    path('address/create/<int:user_id>/', views.CreateAddressView.as_view(), name='create-address'),
    path('address/<int:user_id>/<int:address_id>/', views.UpdateAddressView.as_view(), name='update-address'),
    path('address/<int:user_id>/<int:address_id>/delete/', views.DeleteAddressView.as_view(), name='delete-address'),
    path('address/<int:user_id>/<int:address_id>/default/', views.SetDefaultAddressView.as_view(), name='set-default-address'),
    path('checkout/preview/', views.OrderConfirmationPreviewView.as_view(), name='checkout-preview'),
    path('checkout/address/', views.CheckoutWithAddressView.as_view(), name='checkout-with-address'),
    
    # ==================== NOTIFICATIONS ENDPOINTS ====================
    path('notifications/register/<int:user_id>/', views.RegisterDeviceTokenView.as_view(), name='register-device-token'),
    path('notifications/register/', views.RegisterDeviceTokenView.as_view(), name='register-device-token-no-user'),
    
    # ==================== GPS LOCATION DETECTION ENDPOINTS ====================
    # path('location/detect/<int:user_id>/', views.DetectCurrentLocationView.as_view(), name='detect-location'),
    # path('location/confirm-address/<int:user_id>/', views.ConfirmLocationAddressView.as_view(), name='confirm-location-address'),
    # path('location/nearby-addresses/<int:user_id>/', views.NearbyAddressesView.as_view(), name='nearby-addresses'),
    
    # ==================== PRODUCT ENDPOINTS ====================
    path('products/', views.AllProductsView.as_view(), name='all-products'),
    path('search/<int:user_id>/', views.SearchProductsView.as_view(), name='search-products'),
    path('search/popular/', views.PopularSearchView.as_view(), name='popular-search'),
    path('search/log/', views.LogSearchView.as_view(), name='log-search'),
    
    # ==================== RECOMMENDATION ENDPOINTS ====================
    path('recommendations/for-you/<int:user_id>/', views.PersonalizedRecommendationsView.as_view(), name='personalized-recommendations'),
    path('recommendations/frequently-bought/<int:user_id>/', views.FrequentlyBoughtTogetherView.as_view(), name='frequently-bought-together'),
    path('recommendations/top-selling/', views.TopSellingProductsView.as_view(), name='top-selling-products'),
    path('recommendations/popular/', views.PopularProductsView.as_view(), name='popular-products'),
    path('recommendations/recently-viewed/<int:user_id>/', views.RecentlyViewedView.as_view(), name='recently-viewed'),
    path('recommendations/user-activity/<int:user_id>/', views.UserRecentActivityView.as_view(), name='user-activity'),
    
    # Category List for Retailers
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/<int:user_id>/', views.CategoryListView.as_view(), name='category-list-with-user'),

    # Related products (category-based, user-specific)
    path('products/<str:product_id>/related/<int:user_id>/', views.related_products, name='related-products'),
]
