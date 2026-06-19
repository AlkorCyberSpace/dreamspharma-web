from django.urls import path
from . import views

urlpatterns = [
    # Payment Initiation and Verification
    path('initiate/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('verify/', views.VerifyPaymentView.as_view(), name='verify-payment'),
    
    # Payment Status - multiple lookup options
    path('status/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('status/order/<str:order_id>/', views.PaymentStatusView.as_view(), name='payment-status-by-order'),
    path('status/payment/<str:payment_id>/', views.PaymentStatusView.as_view(), name='payment-status-by-payment-id'),
    
    # Refund Management
    path('refund/', views.InitiateRefundView.as_view(), name='initiate-refund'),
    
    # Cash on Delivery (COD) Payment
    path('cod/initiate/', views.InitiateCODPaymentView.as_view(), name='initiate-cod'),
    path('cod/confirm/', views.ConfirmCODPaymentView.as_view(), name='confirm-cod'),
    
    # Webhook
    path('webhook/', views.WebhookView.as_view(), name='razorpay-webhook'),
]