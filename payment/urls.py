from django.urls import path
from . import views

urlpatterns = [
    # Payment Initiation and Verification
    path('initiate/<int:user_id>/', views.InitiatePaymentView.as_view(), name='initiate-payment'),
    path('verify/<int:user_id>/', views.VerifyPaymentView.as_view(), name='verify-payment'),
    
    # Payment Status - multiple lookup options
    path('status/<int:user_id>/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('status/order/<int:user_id>/<str:order_id>/', views.PaymentStatusView.as_view(), name='payment-status-by-order'),
    path('status/payment/<int:user_id>/<str:payment_id>/', views.PaymentStatusView.as_view(), name='payment-status-by-payment-id'),
    
    # Refund Management
    path('refund/<int:user_id>/', views.InitiateRefundView.as_view(), name='initiate-refund'),
    
    # Cash on Delivery (COD) Payment
    path('cod/initiate/<int:user_id>/', views.InitiateCODPaymentView.as_view(), name='initiate-cod'),
    path('cod/confirm/<int:user_id>/', views.ConfirmCODPaymentView.as_view(), name='confirm-cod'),
    
    # Webhook
    path('webhook/', views.WebhookView.as_view(), name='razorpay-webhook'),
]