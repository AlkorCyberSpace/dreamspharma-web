from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db import transaction
from django.db.models import Sum
import hashlib
import hmac
from decimal import Decimal, InvalidOperation
import uuid
import logging

from .models import Payment, PaymentLog, PaymentRefund
from dreamspharmaapp.models import SalesOrder
from .serializers import PaymentSerializer, PaymentLogSerializer, PaymentRefundSerializer

logger = logging.getLogger(__name__)

# Lazy import to avoid pkg_resources dependency issues
def get_razorpay_client():
    import razorpay
    return razorpay

def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def verify_webhook_signature(request):
    """Verify Razorpay webhook signature"""
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    received_signature = request.headers.get('X-Razorpay-Signature')
    
    if not received_signature:
        return False
    
    body = request.body
    if isinstance(body, str):
        body = body.encode()
    
    generated_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(generated_signature, received_signature)


class RazorpayClient:
    """Razorpay API client wrapper"""
    
    def __init__(self):
        razorpay = get_razorpay_client()
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    
    def create_order(self, amount, currency='INR', receipt=None, notes=None):
        """Create Razorpay order"""
        data = {
            'amount': int(amount * 100),  # Amount in paise
            'currency': currency,
            'receipt': receipt or '',
            'notes': notes or {}
        }
        return self.client.order.create(data=data)
    
    def fetch_order(self, order_id):
        """Fetch order details"""
        return self.client.order.fetch(order_id)
    
    def verify_payment_signature(self, order_id, payment_id, signature):
        """Verify payment signature"""
        data = f"{order_id}|{payment_id}"
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return generated_signature == signature
    
    def refund_payment(self, payment_id, amount=None, notes=None):
        """Initiate refund"""
        data = {}
        if amount:
            data['amount'] = int(amount * 100)
        if notes:
            data['notes'] = notes
        
        return self.client.payment.refund(payment_id, data=data)
    
    def fetch_payment(self, payment_id):
        """Fetch payment details"""
        return self.client.payment.fetch(payment_id)


class InitiatePaymentView(APIView):
    """Initiate payment for an order"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            order_id = request.data.get('order_id')
            if not order_id:
                return Response(
                    {'error': 'order_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sales_order = get_object_or_404(SalesOrder, order_id=order_id)
            
            # Check for existing successful payment
            existing_payment = Payment.objects.filter(
                sales_order=sales_order,
                status='SUCCESS'
            ).first()
            
            if existing_payment:
                return Response(
                    {'error': 'Payment already completed for this order'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check for pending/failed payments - allow retry but track attempts
            pending_payment = Payment.objects.filter(
                sales_order=sales_order,
                status__in=['PENDING', 'INITIATED']
            ).first()
            
            if pending_payment:
                # Increment retry count if payment exists
                if pending_payment.retry_count >= 5:
                    return Response(
                        {'error': 'Maximum payment attempts exceeded. Please contact support.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                payment = pending_payment
                payment.retry_count += 1
                logger.info(f"[PAYMENT_RETRY] Order {order_id} - Attempt #{payment.retry_count}")
            else:
                # Create new payment record
                merchant_ref_id = f"MER-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
                payment = Payment.objects.create(
                    user=request.user,
                    sales_order=sales_order,
                    amount=sales_order.order_total,
                    customer_name=sales_order.patient_name,
                    customer_email=sales_order.patient_email,
                    customer_phone=sales_order.mobile_no,
                    customer_address=sales_order.patient_address,
                    customer_ip=get_client_ip(request),
                    customer_user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    merchant_reference_id=merchant_ref_id,
                    status='INITIATED',
                    retry_count=1
                )
                logger.info(f"[PAYMENT_INITIATED] Order {order_id} - Merchant Ref: {merchant_ref_id}")
            
            # Create Razorpay order
            razorpay_client = RazorpayClient()
            razorpay_order = razorpay_client.create_order(
                amount=float(sales_order.order_total),
                receipt=f"Order-{sales_order.order_id}",
                notes={
                    'order_id': sales_order.order_id,
                    'user_id': str(request.user.id),
                    'customer_name': sales_order.patient_name
                }
            )
            
            # Update payment with Razorpay order ID and expiry
            payment.razorpay_order_id = razorpay_order['id']
            payment.status = 'PENDING'
            payment.expiry_at = timezone.now() + timezone.timedelta(minutes=15)  # Razorpay default expiry
            payment.save()
            
            # Log the request
            PaymentLog.objects.create(
                payment=payment,
                operation='CREATE_ORDER',
                request_data={'order_id': order_id},
                response_data=razorpay_order,
                response_status_code=razorpay_order.get('status_code', 201),
                success=True
            )
            
            return Response({
                'payment_id': str(payment.payment_id),
                'razorpay_order_id': razorpay_order['id'],
                'amount': float(payment.amount),
                'currency': payment.currency,
                'key_id': settings.RAZORPAY_KEY_ID,
                'customer_name': payment.customer_name,
                'customer_email': payment.customer_email,
                'customer_phone': payment.customer_phone
            }, status=status.HTTP_201_CREATED)
        
        except Http404:
            raise
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyPaymentView(APIView):
    """Verify payment signature and complete payment"""
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            payment_id = request.data.get('payment_id')
            razorpay_order_id = request.data.get('razorpay_order_id')
            razorpay_payment_id = request.data.get('razorpay_payment_id')
            razorpay_signature = request.data.get('razorpay_signature')
            
            # Validate required fields
            if not all([payment_id, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                return Response(
                    {'error': 'Missing required payment verification details'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get payment record
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                user=request.user
            )
            
            # Verify signature
            razorpay_client = RazorpayClient()
            if not razorpay_client.verify_payment_signature(
                razorpay_order_id,
                razorpay_payment_id,
                razorpay_signature
            ):
                payment.status = 'FAILED'
                payment.error_description = 'Payment signature verification failed'
                payment.save()
                
                PaymentLog.objects.create(
                    payment=payment,
                    operation='VERIFY_PAYMENT',
                    request_data={
                        'razorpay_order_id': razorpay_order_id,
                        'razorpay_payment_id': razorpay_payment_id
                    },
                    success=False,
                    error_message='Signature verification failed'
                )
                
                return Response(
                    {'error': 'Payment verification failed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Fetch payment details from Razorpay
            payment_details = razorpay_client.fetch_payment(razorpay_payment_id)
            
            # Update payment record
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.payment_completed_at = timezone.now()
            
            # Set status based on payment capture status
            if payment_details.get('status') == 'captured':
                payment.status = 'SUCCESS'
            else:
                payment.status = 'FAILED'
            
            if payment.status == 'FAILED':
                payment.error_code = payment_details.get('error_code')
                payment.error_description = payment_details.get('error_description')
            
            payment.save()
            
            # Log verification
            PaymentLog.objects.create(
                payment=payment,
                operation='VERIFY_PAYMENT',
                request_data={
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id
                },
                response_data=payment_details,
                response_status_code=200,
                success=payment.status == 'SUCCESS',
                error_message=None if payment.status == 'SUCCESS' else payment.error_description
            )
            
            # Update sales order status if payment successful
            if payment.status == 'SUCCESS' and payment.sales_order:
                payment.sales_order.ord_conversion_flag = True
                payment.sales_order.save()
            
            return Response({
                'success': payment.status == 'SUCCESS',
                'payment_id': str(payment.payment_id),
                'status': payment.status,
                'amount': float(payment.amount),
                'message': 'Payment verified successfully' if payment.status == 'SUCCESS' else 'Payment verification failed'
            }, status=status.HTTP_200_OK)
        
        except Http404:
            raise
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaymentStatusView(APIView):
    """Get payment status"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id=None, payment_id=None):
        try:
            if not order_id and not payment_id:
                # Get all payments for user
                payments = Payment.objects.filter(user=request.user)
                serializer = PaymentSerializer(payments, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            # Get payment by order_id or payment_id
            if order_id:
                # Use filter + order_by to handle multiple payments per order (retries)
                payment = Payment.objects.filter(
                    sales_order__order_id=order_id,
                    user=request.user
                ).order_by('-created_at').first()
                
                if not payment:
                    return Response(
                        {'error': 'No payment found for this order'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                payment = get_object_or_404(
                    Payment,
                    payment_id=payment_id,
                    user=request.user
                )
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Http404:
            raise
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InitiateRefundView(APIView):
    """Initiate refund for a payment"""
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            payment_id = request.data.get('payment_id')
            amount = request.data.get('amount')
            reason = request.data.get('reason', 'Customer requested refund')
            
            if not payment_id:
                return Response(
                    {'error': 'payment_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                user=request.user,
                status='SUCCESS'
            )
            
            # Convert and validate refund amount
            refund_amount = payment.amount
            if amount:
                try:
                    amount_decimal = Decimal(str(amount))
                except (InvalidOperation, ValueError):
                    return Response(
                        {'error': 'Invalid refund amount'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if amount_decimal > payment.amount:
                    return Response(
                        {'error': 'Refund amount cannot exceed payment amount'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                refund_amount = amount_decimal
            
            # Check cumulative refunds to prevent over-refunding
            existing_refunds_total = PaymentRefund.objects.filter(
                payment=payment,
                status__in=['INITIATED', 'PENDING', 'SUCCESS']
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            remaining_refundable = payment.amount - existing_refunds_total
            
            if refund_amount > remaining_refundable:
                return Response(
                    {'error': f'Refund amount exceeds remaining refundable amount. Remaining: {remaining_refundable}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Initiate refund via Razorpay
            razorpay_client = RazorpayClient()
            razorpay_refund = razorpay_client.refund_payment(
                payment.razorpay_payment_id,
                amount=float(refund_amount),
                notes={'reason': reason}
            )
            
            # Determine refund type
            is_full_refund = refund_amount == payment.amount
            refund_type = 'FULL' if is_full_refund else 'PARTIAL'
            
            # Create refund record
            refund = PaymentRefund.objects.create(
                payment=payment,
                amount=refund_amount,
                reason=reason,
                razorpay_refund_id=razorpay_refund.get('id'),
                refund_type=refund_type,
                status='INITIATED',
                initiated_by=str(request.user.id),
                response_notes=razorpay_refund
            )
            
            # Update payment status if full refund
            if is_full_refund:
                payment.status = 'REFUNDED'
                payment.save()
                logger.info(f"[FULL_REFUND] Payment {payment.payment_id} - Amount: {refund_amount}")
            else:
                logger.info(f"[PARTIAL_REFUND] Payment {payment.payment_id} - Refunded: {refund_amount}/{payment.amount}")
            
            # Track refund in log
            logger.info(f"[REFUND_INITIATED] Order {payment.sales_order.order_id if payment.sales_order else 'N/A'} - Type: {refund_type}")
            
            # Log refund
            PaymentLog.objects.create(
                payment=payment,
                operation='REFUND',
                request_data={'amount': float(refund_amount), 'reason': reason},
                response_data=razorpay_refund,
                response_status_code=razorpay_refund.get('status_code', 201),
                success=True
            )
            
            serializer = PaymentRefundSerializer(refund)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WebhookView(APIView):
    """Razorpay webhook handler"""
    authentication_classes = []
    permission_classes = []
    
    def post(self, request):
        try:
            # Verify webhook signature
            if not verify_webhook_signature(request):
                return Response(
                    {'error': 'Invalid webhook signature'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            payload = request.data
            event = payload.get('event')
            
            # Create webhook log (will be linked to payment if found)
            webhook_log = PaymentLog.objects.create(
                payment=None,
                operation='WEBHOOK',
                request_data=payload,
                success=True
            )
            
            if event == 'payment.authorized':
                order_id = payload['payload']['payment']['entity'].get('order_id')
                payment_details = payload['payload']['payment']['entity']
                
                payment = Payment.objects.filter(
                    razorpay_order_id=order_id
                ).first()
                
                if payment:
                    payment.razorpay_payment_id = payment_details.get('id')
                    payment.status = 'SUCCESS'
                    payment.payment_completed_at = timezone.now()
                    payment.save()
                    
                    # Link webhook log to payment
                    webhook_log.payment = payment
                    webhook_log.save()
                    
                    # Update sales order
                    if payment.sales_order:
                        payment.sales_order.ord_conversion_flag = True
                        payment.sales_order.save()
            
            elif event == 'payment.failed':
                order_id = payload['payload']['payment']['entity'].get('order_id')
                payment_details = payload['payload']['payment']['entity']
                
                payment = Payment.objects.filter(
                    razorpay_order_id=order_id
                ).first()
                
                if payment:
                    payment.status = 'FAILED'
                    payment.error_code = payment_details.get('error_code')
                    payment.error_description = payment_details.get('error_description')
                    payment.save()
                    
                    # Link webhook log to payment
                    webhook_log.payment = payment
                    webhook_log.save()
            
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        
        except Http404:
            raise
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InitiateCODPaymentView(APIView):
    """Initiate Cash on Delivery payment for an order"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create COD payment record"""
        try:
            order_id = request.data.get('order_id')
            if not order_id:
                return Response(
                    {'error': 'order_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sales_order = get_object_or_404(SalesOrder, order_id=order_id)
            
            # Check for existing successful payment
            existing_payment = Payment.objects.filter(
                sales_order=sales_order,
                status='SUCCESS'
            ).first()
            
            if existing_payment:
                return Response(
                    {'error': 'Payment already completed for this order'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check for existing COD payment
            existing_cod = Payment.objects.filter(
                sales_order=sales_order,
                payment_method='COD',
                status__in=['INITIATED', 'PENDING']
            ).first()
            
            if existing_cod:
                return Response(
                    {'error': 'COD payment already initiated for this order'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            merchant_ref_id = f"COD-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            # Create COD payment record
            with transaction.atomic():
                payment = Payment.objects.create(
                    user=request.user,
                    sales_order=sales_order,
                    amount=sales_order.order_total,
                    payment_method='COD',
                    status='PENDING',  # COD starts as PENDING (awaiting delivery)
                    customer_name=sales_order.patient_name,
                    customer_email=sales_order.patient_email,
                    customer_phone=sales_order.mobile_no,
                    customer_address=sales_order.patient_address,
                    customer_ip=get_client_ip(request),
                    customer_user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    merchant_reference_id=merchant_ref_id,
                    retry_count=1
                )
                
                # Log the COD initiation
                PaymentLog.objects.create(
                    payment=payment,
                    operation='CREATE_ORDER',
                    request_data={'order_id': order_id, 'payment_method': 'COD'},
                    response_data={'status': 'COD_INITIATED', 'merchant_ref_id': merchant_ref_id},
                    response_status_code=201,
                    success=True
                )
                
                logger.info(f"[COD_INITIATED] Order {order_id} - Merchant Ref: {merchant_ref_id} - Amount: ₹{sales_order.order_total}")
                
                return Response({
                    'success': True,
                    'payment_id': str(payment.payment_id),
                    'order_id': sales_order.order_id,
                    'payment_method': 'COD',
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'customer_name': payment.customer_name,
                    'customer_phone': payment.customer_phone,
                    'status': 'PENDING',
                    'message': 'COD payment initiated. Payment will be collected at delivery.'
                }, status=status.HTTP_201_CREATED)
        
        except Http404:
            raise
        except Exception as e:
            logger.error(f"[COD_ERROR] Error initiating COD: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConfirmCODPaymentView(APIView):
    """Confirm COD payment collection (called after delivery)"""
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        """Mark COD payment as collected"""
        try:
            payment_id = request.data.get('payment_id')
            collected_by = request.data.get('collected_by', 'Delivery Agent')
            
            if not payment_id:
                return Response(
                    {'error': 'payment_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get payment record - allow staff/admin or the payment owner
            payment = get_object_or_404(
                Payment,
                payment_id=payment_id,
                payment_method='COD'
            )
            
            # Only staff/admin or the payment owner can confirm COD
            if not request.user.is_staff and payment.user != request.user:
                return Response(
                    {'error': 'You do not have permission to confirm this payment'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if payment.status == 'SUCCESS':
                return Response(
                    {'error': 'Payment already confirmed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if payment.status not in ['PENDING', 'INITIATED']:
                return Response(
                    {'error': f'Cannot confirm payment with status: {payment.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update payment status
            payment.status = 'SUCCESS'
            payment.cod_collected = True
            payment.cod_collected_at = timezone.now()
            payment.cod_collected_by = collected_by
            payment.payment_completed_at = timezone.now()
            payment.save()
            
            # Update sales order conversion flag
            if payment.sales_order:
                payment.sales_order.ord_conversion_flag = True
                payment.sales_order.save()
            
            # Log the payment confirmation
            PaymentLog.objects.create(
                payment=payment,
                operation='VERIFY_PAYMENT',
                request_data={'collected_by': collected_by},
                response_data={'status': 'COD_CONFIRMED'},
                response_status_code=200,
                success=True
            )
            
            logger.info(f"[COD_COLLECTED] Payment {payment.payment_id} - Amount: ₹{payment.amount} - Collected by: {collected_by}")
            
            return Response({
                'success': True,
                'message': 'COD payment collected successfully',
                'payment_id': str(payment.payment_id),
                'order_id': payment.sales_order.order_id,
                'amount': float(payment.amount),
                'collected_at': payment.cod_collected_at.isoformat(),
                'collected_by': payment.cod_collected_by
            }, status=status.HTTP_200_OK)
        
        except Http404:
            raise
        except Exception as e:
            logger.error(f"[COD_CONFIRM_ERROR] Error confirming COD: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )