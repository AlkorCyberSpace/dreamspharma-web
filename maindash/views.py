from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth import get_user_model, logout
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
import openpyxl
from io import BytesIO
from django.db.models import Sum, Count, Q, Avg, Max, F, DecimalField
from django.db.models.functions import TruncMonth, TruncYear
from django.utils.dateparse import parse_date
from datetime import timedelta, date
from dreamspharmaapp.models import KYC, SalesOrder, Category, ItemMaster, ProductInfo, Offer, Invoice, SalesOrderItem, InvoiceDetail, CreditNote
from .models import AuditLog, AdminNotification
from .serializers import (
    RetailerKYCDetailSerializer, ApproveKYCSerializer, RejectKYCSerializer,
    DashboardStatisticsSerializer, ChangePasswordSerializer, SuperAdminProfileSerializer,
    SuperAdminProfileImageSerializer, AddCategorySerializer, AuditLogSerializer,
    AdminNotificationSerializer
)
from dreamspharmaapp.serializers import OfferSerializer, OfferCreateUpdateSerializer, OfferListSerializer
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: write an audit log entry (silent – never breaks the calling view)
# ---------------------------------------------------------------------------
def log_audit(action, performed_by_user=None, target_entity='', details='', category='System'):
    """
    Create an AuditLog record.  Called inside every admin action.
    `performed_by_user` may be a CustomUser instance or None (for system actions).
    """
    try:
        if performed_by_user and performed_by_user.is_authenticated:
            performed_by_label = performed_by_user.get_full_name() or performed_by_user.username
        else:
            performed_by_label = 'System'

        AuditLog.objects.create(
            action=action,
            performed_by=performed_by_label,
            performed_by_user=performed_by_user if (performed_by_user and performed_by_user.is_authenticated) else None,
            target_entity=target_entity,
            details=details,
            category=category,
        )
    except Exception as exc:
        logger.error(f"[AUDIT_LOG_FAILED] {exc}")


class SuperAdminGetAllRetailersView(APIView):
    """
    API endpoint for superadmin to get all retailers' KYC plus registration details.
    GET /api/superadmin/retailers/ - Get all retailers' KYC and registration details
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all retailers with their KYC and registration details"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all retailers with KYC submitted
        retailers_kyc = KYC.objects.select_related('user').all().order_by('-submitted_at')
        
        if not retailers_kyc.exists():
            return Response({
                'message': 'No retailers with KYC found',
                'count': 0,
                'results': []
            }, status=status.HTTP_200_OK)
        
        serializer = RetailerKYCDetailSerializer(retailers_kyc, many=True)
        
        return Response({
            'message': 'All retailers KYC and registration details',
            'count': retailers_kyc.count(),
            'results': serializer.data
        }, status=status.HTTP_200_OK)


class ApproveKYCView(APIView):
    """
    API endpoint for superadmin to approve KYC.
    POST /api/superadmin/kyc/approve/<user_id>/ - Approve a retailer's KYC
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Approve KYC for a retailer"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can approve KYC'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = {'user_id': user_id}
        serializer = ApproveKYCSerializer(data=data)
        
        if serializer.is_valid():
            kyc = serializer.save()
            kyc_serializer = RetailerKYCDetailSerializer(kyc)

            # ── Audit log ──
            shop = getattr(kyc, 'shop_name', '') or ''
            log_audit(
                action='KYC Approved',
                performed_by_user=request.user,
                target_entity=f"{shop} (RET{str(user_id).zfill(3)})",
                details='All documents verified and approved',
                category='KYC',
            )

            return Response({
                'message': 'KYC approved successfully',
                'kyc': kyc_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Failed to approve KYC',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class RejectKYCView(APIView):
    """
    API endpoint for superadmin to reject KYC.
    POST /api/superadmin/kyc/reject/<user_id>/ - Reject a retailer's KYC with reason
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        """Reject KYC for a retailer"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can reject KYC'
            }, status=status.HTTP_403_FORBIDDEN)
        
        data = {'user_id': user_id, **request.data}
        serializer = RejectKYCSerializer(data=data)
        
        if serializer.is_valid():
            kyc = serializer.save()
            kyc_serializer = RetailerKYCDetailSerializer(kyc)

            # ── Audit log ──
            shop = getattr(kyc, 'shop_name', '') or ''
            reason = request.data.get('rejection_reason', 'No reason provided')
            log_audit(
                action='KYC Rejected',
                performed_by_user=request.user,
                target_entity=f"{shop} (RET{str(user_id).zfill(3)})",
                details=f"{reason}",
                category='KYC',
            )

            return Response({
                'message': 'KYC rejected successfully',
                'kyc': kyc_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Failed to reject KYC',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DashboardStatisticsView(APIView):
    """
    API endpoint for superadmin to get dashboard statistics.
    GET /api/superadmin/dashboard/statistics/ - Get dashboard statistics
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics for superadmin"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        now = timezone.now()
        last_7_days = now - timedelta(days=7)
        prev_7_days = now - timedelta(days=14)

        # 1. Total Retailers (Approved Only as requested)
        total_retailers = User.objects.filter(role='RETAILER', is_kyc_approved=True).count()
        prev_retailers = User.objects.filter(role='RETAILER', is_kyc_approved=True, created_at__lt=last_7_days).count()
        
        # 2. Pending KYC
        pending_kyc = KYC.objects.filter(status='PENDING').count()
        prev_pending_kyc = KYC.objects.filter(status='PENDING', submitted_at__lt=last_7_days).count()
        
        # 3. Total Orders
        total_orders = SalesOrder.objects.count()
        prev_total_orders = SalesOrder.objects.filter(created_at__lt=last_7_days).count()
        curr_week_orders = SalesOrder.objects.filter(created_at__gte=last_7_days).count()
        prev_week_orders = SalesOrder.objects.filter(created_at__gte=prev_7_days, created_at__lt=last_7_days).count()
        
        # 4. Orders in Dispatch (Invoice exists but not Delivered)
        orders_in_dispatch = SalesOrder.objects.filter(invoices__isnull=False, dc_conversion_flag=False).distinct().count()
        prev_dispatch = SalesOrder.objects.filter(invoices__isnull=False, dc_conversion_flag=False, created_at__lt=last_7_days).distinct().count()

        # 5. Top Selling Product (Current Week)
        # Since SalesOrderItem.item_name might be empty, we need to fetch from ItemMaster
        # Use raw SQL to join SalesOrderItem with ItemMaster
        from django.db import connection
        
        cursor = connection.cursor()
        cursor.execute("""
            SELECT soi.item_code, im.item_name, SUM(soi.total_loose_qty) as total_qty
            FROM dreamspharmaapp_salesorderitem soi
            LEFT JOIN dreamspharmaapp_itemmaster im ON soi.item_code = im.item_code
            JOIN dreamspharmaapp_salesorder so ON soi.sales_order_id = so.id
            WHERE so.ord_date >= %s
            AND (im.item_name IS NOT NULL AND im.item_name != '')
            GROUP BY soi.item_code, im.item_name
            ORDER BY total_qty DESC
            LIMIT 1
        """, [last_7_days.date()])
        
        top_product_entry = None
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            top_product_entry = dict(zip(columns, row))
        
        top_selling_product = (top_product_entry['item_name'] or 'N/A') if top_product_entry else "N/A"
        current_week_qty = top_product_entry['total_qty'] if top_product_entry else 0
        
        # Compare with previous week for the same product
        prev_week_qty = 0
        if top_product_entry and top_product_entry.get('item_code'):
            prev_product = SalesOrderItem.objects.filter(
                sales_order__ord_date__gte=prev_7_days.date(),
                sales_order__ord_date__lt=last_7_days.date(),
                item_code=top_product_entry['item_code']
            ).aggregate(total=Sum('total_loose_qty'))['total'] or 0
            prev_week_qty = prev_product if prev_product else 0
        
        # Calculate Percentages
        def calc_pct(curr, prev):
            if prev == 0: return 100.0 if curr > 0 else 0.0
            return round(((curr - prev) / prev) * 100, 1)

        def get_trend_text(curr, prev):
            diff = curr - prev
            return f"{'+' if diff >= 0 else ''}{diff} from last week"

        # Preparing stats payload
        stats_data = {
            'total_retailers': total_retailers,
            'retailers_change_percentage': calc_pct(total_retailers, prev_retailers),
            'retailers_change_text': get_trend_text(total_retailers, prev_retailers),
            
            'pending_kyc': pending_kyc,
            'pending_kyc_change': pending_kyc - prev_pending_kyc,
            'pending_kyc_change_text': f"{pending_kyc - prev_pending_kyc} from last week",
            
            'total_orders': total_orders,
            'orders_change_percentage': calc_pct(curr_week_orders, prev_week_orders),
            'orders_change_text': get_trend_text(curr_week_orders, prev_week_orders),

            'orders_in_dispatch': orders_in_dispatch,
            'dispatch_change_percentage': calc_pct(orders_in_dispatch, prev_dispatch),
            'dispatch_change_text': get_trend_text(orders_in_dispatch, prev_dispatch),

            'top_selling_product': top_selling_product,
            'top_selling_change_percentage': calc_pct(current_week_qty, prev_week_qty),

            # Daily Order Volume Graph (Last 7 days)
            'daily_order_volume': [],
            
            # Orders by Status Pie Chart
            'orders_by_status': []
        }

        # Populate Daily Order Volume
        for i in range(6, -1, -1):
            date = (now - timedelta(days=i)).date()
            count = SalesOrder.objects.filter(ord_date=date).count()
            stats_data['daily_order_volume'].append({
                'date': date.strftime('%b %d'),
                'orders': count
            })

        # Populate Status Distribution
        status_counts = {
            'Pending': SalesOrder.objects.filter(ord_conversion_flag=False).count(),
            'Confirmed': SalesOrder.objects.filter(ord_conversion_flag=True, invoices__isnull=True).count(),
            'Dispatched': SalesOrder.objects.filter(invoices__isnull=False, dc_conversion_flag=False).distinct().count(),
            'Delivered': SalesOrder.objects.filter(dc_conversion_flag=True).count(),
        }
        
        total_stat_orders = sum(status_counts.values())
        for status_label, count in status_counts.items():
            pct = round((count / total_stat_orders * 100), 1) if total_stat_orders > 0 else 0
            stats_data['orders_by_status'].append({
                'status': status_label,
                'count': count,
                'percentage': pct
            })

        # Income/Expense by Category (for donut chart)
        income_expense_data = {}
        
        # Calculate Income by Category (from invoices)
        invoice_details = InvoiceDetail.objects.select_related(
            'invoice__sales_order'
        ).filter(
            invoice__sales_order__ord_date__gte=timezone.now().date() - timedelta(days=30)
        ).values(
            'product_name'
        ).annotate(
            total_income=Sum('item_total', output_field=DecimalField())
        )
        
        for detail in invoice_details:
            product_name = detail['product_name']
            income = float(detail['total_income'] or 0)
            
            if product_name not in income_expense_data:
                income_expense_data[product_name] = {'income': 0, 'expense': 0}
            income_expense_data[product_name]['income'] += income
        
        # Calculate Expense by Category (from credit notes - refunds)
        credit_notes = CreditNote.objects.filter(
            status__in=['APPROVED', 'DELIVERED'],
            created_at__gte=timezone.now().date() - timedelta(days=30)
        ).values('product_name').annotate(
            total_refund=Sum('amount', output_field=DecimalField())
        )
        
        for note in credit_notes:
            product_name = note['product_name']
            expense = float(note['total_refund'] or 0)
            
            if product_name not in income_expense_data:
                income_expense_data[product_name] = {'income': 0, 'expense': 0}
            income_expense_data[product_name]['expense'] += expense
        
        # Format for donut chart
        income_by_category = []
        expense_by_category = []
        
        for product_name, values in sorted(income_expense_data.items()):
            if values['income'] > 0:
                income_by_category.append({
                    'name': product_name,
                    'value': round(values['income'], 2),
                    'percentage': 0  # Will calculate after
                })
            if values['expense'] > 0:
                expense_by_category.append({
                    'name': product_name,
                    'value': round(values['expense'], 2),
                    'percentage': 0  # Will calculate after
                })
        
        # Calculate percentages
        total_income = sum(item['value'] for item in income_by_category)
        total_expense = sum(item['value'] for item in expense_by_category)
        
        for item in income_by_category:
            item['percentage'] = round((item['value'] / total_income * 100), 1) if total_income > 0 else 0
        
        for item in expense_by_category:
            item['percentage'] = round((item['value'] / total_expense * 100), 1) if total_expense > 0 else 0
        
        # Sort by value descending and take top 5
        income_by_category = sorted(income_by_category, key=lambda x: x['value'], reverse=True)[:5]
        expense_by_category = sorted(expense_by_category, key=lambda x: x['value'], reverse=True)[:5]
        
        stats_data['income_by_category'] = income_by_category
        stats_data['expense_by_category'] = expense_by_category
        stats_data['total_income'] = round(total_income, 2)
        stats_data['total_expense'] = round(total_expense, 2)

        serializer = DashboardStatisticsSerializer(stats_data)
        return Response({
            'success': True,
            'message': 'Dashboard statistics fetched successfully',
            'statistics': serializer.data
        }, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    API endpoint for super admin to change password.
    POST /api/superadmin/change-password/ - Change password for logged-in super admin
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Change password for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
                return Response({
                    'message': 'Password changed successfully'
                }, status=status.HTTP_200_OK)
            except serializers.ValidationError as e:
                return Response({
                    'error': str(e.detail[0])
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'error': 'Password change failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class GetSuperAdminProfileView(APIView):
    """
    API endpoint for super admin to get and update profile information.
    GET /api/superadmin/profile/ - Get super admin profile info (username, email, phone, image)
    PUT /api/superadmin/profile/ - Update super admin profile info (email, first_name, last_name, phone_number)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get profile information for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileSerializer(request.user)
        
        return Response({
            'message': 'Profile information fetched successfully',
            'profile': serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        """Update profile information for super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            try:
                serializer.save()
                
                # ── Audit log ──
                log_audit(
                    action='Profile Updated',
                    performed_by_user=request.user,
                    target_entity=request.user.username,
                    details='Super admin updated their profile information',
                    category='Profile',
                )
                
                logger.info(f"[PROFILE_UPDATED] User: {request.user.username}")
                
                return Response({
                    'message': 'Profile updated successfully',
                    'profile': serializer.data
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error updating profile: {str(e)}")
                return Response({
                    'error': f'Error updating profile: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'error': 'Profile update failed',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageView(APIView):
    """
    Profile Image Management - Upload and Delete
    POST: Upload profile image
    DELETE: Delete profile image
    """
    permission_classes = [IsAuthenticated]

    def _check_superadmin(self, request):
        """Check if user is SUPERADMIN"""
        return request.user.role == 'SUPERADMIN'

    def post(self, request):
        """Upload profile image for super admin"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'uploadProfileImage',
                'message': 'Forbidden - Only SUPERADMIN can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileImageSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            try:
                serializer.save()
                logger.info(f"[PROFILE_IMAGE_UPLOADED] User: {request.user.username}")
                
                return Response({
                    'code': '200',
                    'type': 'uploadProfileImage',
                    'message': 'Profile image uploaded successfully',
                    'data': {
                        'profile_image': serializer.data['profile_image']
                    }
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error uploading profile image: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'uploadProfileImage',
                    'message': f'Error uploading image: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'uploadProfileImage',
            'message': 'Image upload failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update profile image for super admin"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'updateProfileImage',
                'message': 'Forbidden - Only SUPERADMIN can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = SuperAdminProfileImageSerializer(
            request.user, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            try:
                serializer.save()
                logger.info(f"[PROFILE_IMAGE_UPDATED] User: {request.user.username}")
                
                return Response({
                    'code': '200',
                    'type': 'updateProfileImage',
                    'message': 'Profile image updated successfully',
                    'data': {
                        'profile_image': serializer.data['profile_image']
                    }
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Error updating profile image: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'updateProfileImage',
                    'message': f'Error updating image: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'updateProfileImage',
            'message': 'Image update failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Delete profile image for super admin"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'deleteProfileImage',
                'message': 'Forbidden - Only SUPERADMIN can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not request.user.profile_image:
            return Response({
                'code': '404',
                'type': 'deleteProfileImage',
                'message': 'No profile image found to delete'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            if request.user.profile_image.storage.exists(request.user.profile_image.name):
                request.user.profile_image.storage.delete(request.user.profile_image.name)
            
            request.user.profile_image = None
            request.user.save()
            
            logger.info(f"[PROFILE_IMAGE_DELETED] User: {request.user.username}")
            
            return Response({
                'code': '200',
                'type': 'deleteProfileImage',
                'message': 'Profile image deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error deleting profile image: {str(e)}")
            return Response({
                'code': '500',
                'type': 'deleteProfileImage',
                'message': f'Error deleting image: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class SuperAdminLogoutView(APIView):
    """
    API endpoint for super admin to logout.
    POST /api/superadmin/logout/ - Logout super admin
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Logout super admin"""
        # Check if user is a superadmin
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        # ── Audit log ──
        log_audit(
            action='Admin Logout',
            performed_by_user=request.user,
            target_entity='System',
            details=f'Super-admin {request.user.username} logged out',
            category='System',
        )

        logout(request)
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_205_RESET_CONTENT)


class AddCategoryView(APIView):
    """
    Brand/Category Management
    GET: List all categories or get by ID
    POST: Create a new category/brand
    PUT: Update existing category or create if not exists
    DELETE: Delete a category
    SUPERADMIN ONLY
    """
    permission_classes = [IsAuthenticated]
    
    def _check_superadmin(self, request):
        """Check if user is SUPERADMIN"""
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return False
        return True
    
    def get(self, request, category_id=None):
        """Get all categories or specific category by ID"""
        if not self._check_superadmin(request):
            return Response({
                'code': '403',
                'type': 'getCategory',
                'message': 'Forbidden - Only SUPERADMIN can view categories'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            if category_id:
                # Get specific category by ID from URL
                category = Category.objects.get(id=category_id)
                return Response({
                    'code': '200',
                    'type': 'getCategory',
                    'message': 'Category retrieved successfully',
                    'data': {
                        'id': category.id,
                        'name': category.name,
                        'icon': request.build_absolute_uri(category.icon.url) if category.icon else None,
                        'is_active': category.is_active,
                        'created_at': category.created_at
                    }
                }, status=status.HTTP_200_OK)
            else:
                # Get all categories
                categories = Category.objects.all().order_by('-created_at')
                categories_data = [{
                    'id': cat.id,
                    'name': cat.name,
                    'icon': request.build_absolute_uri(cat.icon.url) if cat.icon else None,
                    'is_active': cat.is_active,
                    'created_at': cat.created_at
                } for cat in categories]
                
                return Response({
                    'code': '200',
                    'type': 'getCategory',
                    'message': f'Found {len(categories_data)} categories',
                    'count': len(categories_data),
                    'data': categories_data
                }, status=status.HTTP_200_OK)
        
        except Category.DoesNotExist:
            return Response({
                'code': '404',
                'type': 'getCategory',
                'message': f'Category with ID {category_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error retrieving category: {str(e)}")
            return Response({
                'code': '500',
                'type': 'getCategory',
                'message': f'Error retrieving category: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """Create a new category/brand"""
        if not self._check_superadmin(request):
            return Response({
                'code': '403',
                'type': 'addCategory',
                'message': 'Forbidden - Only SUPERADMIN can add categories'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = AddCategorySerializer(data=request.data)
        if serializer.is_valid():
            try:
                category = serializer.save()
                
                logger.info(f"[CATEGORY_CREATED] Name: {category.name} | Created by: {request.user.username}")

                # ── Audit log ──
                log_audit(
                    action='Category Created',
                    performed_by_user=request.user,
                    target_entity=category.name,
                    details=f'New category "{category.name}" created',
                    category='Category',
                )

                return Response({
                    'code': '200',
                    'type': 'addCategory',
                    'message': 'Category created successfully',
                    'data': {
                        'id': category.id,
                        'name': category.name,
                        'icon': request.build_absolute_uri(category.icon.url) if category.icon else None,
                        'is_active': category.is_active,
                        'created_at': category.created_at
                    }
                }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                logger.error(f"Error creating category: {str(e)}")
                return Response({
                    'code': '500',
                    'type': 'addCategory',
                    'message': f'Error creating category: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'code': '400',
            'type': 'addCategory',
            'message': 'Invalid parameters',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, category_id=None):
        """Update existing category - ID in URL"""
        if not self._check_superadmin(request):
            return Response({
                'code': '403',
                'type': 'updateCategory',
                'message': 'Forbidden - Only SUPERADMIN can update categories'
            }, status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get('name')
        
        # ID is required for PUT (update only)
        if not category_id:
            return Response({
                'code': '400',
                'type': 'updateCategory',
                'message': 'Category ID is required in URL. Use /add-category/{id}/'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not name:
            return Response({
                'code': '400',
                'type': 'updateCategory',
                'message': 'Category name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get existing category
            category = Category.objects.get(id=category_id)
            old_name = category.name
            
            # Only check for duplicates if name is being changed
            if name.lower() != old_name.lower():
                # Check if new name already exists (for other categories)
                if Category.objects.filter(name__iexact=name).exclude(id=category_id).exists():
                    return Response({
                        'code': '400',
                        'type': 'updateCategory',
                        'message': f'Another category with name "{name}" already exists'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update category
            category.name = name
            category.is_active = request.data.get('is_active', category.is_active)
            
            if 'icon' in request.FILES:
                category.icon = request.FILES['icon']
            
            category.save()
            
            logger.info(f"[CATEGORY_UPDATED] ID: {category_id} | Old Name: {old_name} | New Name: {name} | Updated by: {request.user.username}")

            # ── Audit log ──
            log_audit(
                action='Category Updated',
                performed_by_user=request.user,
                target_entity=name,
                details=f'Category renamed from "{old_name}" to "{name}"' if old_name != name else f'Category "{name}" details updated',
                category='Category',
            )

            return Response({
                'code': '200',
                'type': 'updateCategory',
                'message': 'Category updated successfully',
                'data': {
                    'id': category.id,
                    'name': category.name,
                    'icon': request.build_absolute_uri(category.icon.url) if category.icon else None,
                    'is_active': category.is_active,
                    'created_at': category.created_at
                }
            }, status=status.HTTP_200_OK)
        
        except Category.DoesNotExist:
            return Response({
                'code': '404',
                'type': 'updateCategory',
                'message': f'Category with ID {category_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error updating category: {str(e)}")
            return Response({
                'code': '500',
                'type': 'updateCategory',
                'message': f'Error updating category: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, category_id=None):
        """Delete a category - ID in URL"""
        if not self._check_superadmin(request):
            return Response({
                'code': '403',
                'type': 'deleteCategory',
                'message': 'Forbidden - Only SUPERADMIN can delete categories'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # ID is required in URL
        if not category_id:
            return Response({
                'code': '400',
                'type': 'deleteCategory',
                'message': 'Category ID is required in URL. Use /add-category/{id}/'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category = Category.objects.get(id=category_id)
            category_name = category.name
            
            # Check if category is used in any products
            if ProductInfo.objects.filter(category_id=category_id).exists():
                return Response({
                    'code': '409',
                    'type': 'deleteCategory',
                    'message': f'Cannot delete category "{category_name}" - it is assigned to {ProductInfo.objects.filter(category_id=category_id).count()} product(s)'
                }, status=status.HTTP_409_CONFLICT)
            
            category.delete()
            
            logger.info(f"[CATEGORY_DELETED] ID: {category_id} | Name: {category_name} | Deleted by: {request.user.username}")

            # ── Audit log ──
            log_audit(
                action='Category Deleted',
                performed_by_user=request.user,
                target_entity=category_name,
                details=f'Category "{category_name}" permanently deleted',
                category='Category',
            )

            return Response({
                'code': '200',
                'type': 'deleteCategory',
                'message': f'Category "{category_name}" deleted successfully'
            }, status=status.HTTP_200_OK)
        
        except Category.DoesNotExist:
            return Response({
                'code': '404',
                'type': 'deleteCategory',
                'message': f'Category with ID {category_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}")
            return Response({
                'code': '500',
                'type': 'deleteCategory',
                'message': f'Error deleting category: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class AssignBrandToProductView(APIView):
    """
    Assign brand/category to a product
    POST/PUT: Assign brand to product
    SUPERADMIN ONLY
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Assign brand to product"""
        # Check if user is SUPERADMIN
        if getattr(request.user, 'role', None) != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'assignBrandToProduct',
                'message': 'Forbidden - Only SUPERADMIN can assign brands to products'
            }, status=status.HTTP_403_FORBIDDEN)
        
        item_code = request.data.get('c_item_code')
        brand_id = request.data.get('brand_id')
        
        if not item_code or not brand_id:
            return Response({
                'code': '400',
                'type': 'assignBrandToProduct',
                'message': 'c_item_code and brand_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get the item
            item = ItemMaster.objects.get(item_code=item_code)
            
            # Get or create ProductInfo
            product_info, created = ProductInfo.objects.get_or_create(item=item)
            
            # Get the brand/category
            brand = Category.objects.get(id=brand_id)
            
            # Assign brand to product
            product_info.category = brand
            product_info.save()
            
            logger.info(f"[BRAND_ASSIGNED] Item: {item_code} | Brand: {brand.name} | Brand ID: {brand_id} | Assigned by: {request.user.username}")
            
            return Response({
                'code': '200',
                'type': 'assignBrandToProduct',
                'message': 'Brand assigned to product successfully',
                'data': {
                    'c_item_code': item_code,
                    'brand_id': brand.id,
                    'brand_name': brand.name,
                    'brand_logo': request.build_absolute_uri(brand.icon.url) if brand.icon else ''
                }
            }, status=status.HTTP_200_OK)
        
        except ItemMaster.DoesNotExist:
            return Response({
                'code': '404',
                'type': 'assignBrandToProduct',
                'message': f'Item with code {item_code} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Category.DoesNotExist:
            return Response({
                'code': '404',
                'type': 'assignBrandToProduct',
                'message': f'Brand with ID {brand_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            logger.error(f"Error assigning brand to product: {str(e)}")
            return Response({
                'code': '500',
                'type': 'assignBrandToProduct',
                'message': f'Error assigning brand: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        """PUT method - same as POST"""
        return self.post(request)


# ==================== OFFER MANAGEMENT VIEWS ====================

class OfferListCreateView(APIView):
    """
    List all offers or create new offer (SuperAdmin only)
    GET  /api/offers/?user_id=<retailer_id> - Retailers access with user_id (no auth token)
    GET  /api/offers/ with auth token - SuperAdmins access with auth token
    POST /api/offers/ - SuperAdmin only with auth token
    """
    
    def get_permissions(self):
        """
        GET requests: No auth required for retailers, required for superadmins
        POST requests: Auth required (IsAuthenticated)
        """
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get(self, request):
        """Get list of offers - Retailers provide user_id, SuperAdmins use auth token"""
        
        # Check if user is authenticated (SuperAdmin with auth token)
        if request.user and request.user.is_authenticated:
            # SuperAdmin with auth token - allow all offers
            pass
        else:
            # Unauthenticated request - retailer must provide user_id
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response({
                    'status': 'error',
                    'message': 'user_id parameter is required for retailers without authentication'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate user_id belongs to a valid retailer
            try:
                retailer = User.objects.get(id=user_id, role='RETAILER')
            except User.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Invalid user_id or user is not a retailer'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get filter parameters
        placement = request.query_params.get('placement')
        status_filter = request.query_params.get('status')
        category_id = request.query_params.get('category_id')
        
        # Base queryset
        offers = Offer.objects.all()
        
        # Apply filters
        if placement:
            offers = offers.filter(placement=placement)
        
        if status_filter:
            try:
                status_bool = status_filter.lower() == 'true'
                offers = offers.filter(status=status_bool)
            except:
                pass
        
        if category_id:
            offers = offers.filter(category_id=category_id)
        
        # Auto-inactivate expired offers before returning
        for offer in offers:
            offer.auto_inactivate_if_expired()
        
        # Refresh queryset to get updated status
        offers = Offer.objects.all()
        if placement:
            offers = offers.filter(placement=placement)
        if status_filter:
            try:
                status_bool = status_filter.lower() == 'true'
                offers = offers.filter(status=status_bool)
            except:
                pass
        if category_id:
            offers = offers.filter(category_id=category_id)
        
        # Serialize with request context
        serializer = OfferListSerializer(offers, many=True, context={'request': request})
        
        return Response({
            'status': 'success',
            'message': f'Retrieved {offers.count()} offers',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Create new offer (SuperAdmin only) - Requires auth token"""
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return Response({
                'status': 'error',
                'message': 'Authentication required to create offers'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if user is superadmin
        if request.user.role != 'SUPERADMIN' and not request.user.is_superuser:
            return Response({
                'status': 'error',
                'message': 'Only SuperAdmin can create offers. Authentication token required.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = OfferCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            offer = serializer.save()

            # ── Audit log ──
            log_audit(
                action='Offer Created',
                performed_by_user=request.user,
                target_entity=offer.offer_id,
                details=f'Offer "{offer.title}" created (valid {offer.valid_from} – {offer.valid_to})',
                category='Offer',
            )
            
            # ── Send notifications to all retailers ──
            try:
                from dreamspharmaapp.notification_views import send_offer_notification_to_all_retailers
                notification_result = send_offer_notification_to_all_retailers(offer)
            except Exception as e:
                notification_result = {'success': False, 'message': str(e)}

            return Response({
                'status': 'success',
                'message': 'Offer created successfully',
                'data': OfferSerializer(offer).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'status': 'error',
            'message': 'Invalid offer data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OfferDetailView(APIView):
    """
    Get, update, or delete specific offer
    GET    /api/offers/{offer_id}/
    PUT    /api/offers/{offer_id}/
    DELETE /api/offers/{offer_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, offer_id):
        """Get offer by offer_id"""
        try:
            return Offer.objects.get(offer_id=offer_id)
        except Offer.DoesNotExist:
            return None
    
    def get(self, request, offer_id):
        """Get offer details"""
        offer = self.get_object(offer_id)
        if not offer:
            return Response({
                'status': 'error',
                'message': 'Offer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Auto-inactivate if expired
        offer.auto_inactivate_if_expired()
        
        serializer = OfferSerializer(offer)
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def put(self, request, offer_id):
        """Update offer (SuperAdmin only)"""
        # Check permission
        if request.user.role != 'SUPERADMIN' and not request.user.is_superuser:
            return Response({
                'status': 'error',
                'message': 'Only SuperAdmin can update offers'
            }, status=status.HTTP_403_FORBIDDEN)
        
        offer = self.get_object(offer_id)
        if not offer:
            return Response({
                'status': 'error',
                'message': 'Offer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OfferCreateUpdateSerializer(offer, data=request.data, partial=True)
        if serializer.is_valid():
            offer = serializer.save()

            # ── Audit log ──
            log_audit(
                action='Offer Updated',
                performed_by_user=request.user,
                target_entity=offer.offer_id,
                details=f'Offer "{offer.title}" updated',
                category='Offer',
            )
            
            # ── Send notifications to all retailers ──
            try:
                from dreamspharmaapp.notification_views import send_offer_notification_to_all_retailers
                notification_result = send_offer_notification_to_all_retailers(offer)
            except Exception as e:
                notification_result = {'success': False, 'message': str(e)}

            return Response({
                'status': 'success',
                'message': 'Offer updated successfully',
                'data': OfferSerializer(offer).data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'Invalid offer data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, offer_id):
        """Delete offer (SuperAdmin only)"""
        # Check permission
        if request.user.role != 'SUPERADMIN' and not request.user.is_superuser:
            return Response({
                'status': 'error',
                'message': 'Only SuperAdmin can delete offers'
            }, status=status.HTTP_403_FORBIDDEN)
        
        offer = self.get_object(offer_id)
        if not offer:
            return Response({
                'status': 'error',
                'message': 'Offer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        offer_title = offer.title
        offer_id_val = offer.offer_id
        offer.delete()

        # ── Audit log ──
        log_audit(
            action='Offer Deleted',
            performed_by_user=request.user,
            target_entity=offer_id_val,
            details=f'Offer "{offer_title}" deleted',
            category='Offer',
        )

        return Response({
            'status': 'success',
            'message': 'Offer deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class HomePageOffersView(APIView):
    """
    Get active homepage offers (Public endpoint)
    GET /api/offers/homepage/
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Get active homepage offers"""
        today = timezone.now().date()
        
        # Get active homepage offers that are currently valid
        offers = Offer.objects.filter(
            status=True,
            placement='homepage',
            valid_from__lte=today,
            valid_to__gte=today
        )
        
        serializer = OfferListSerializer(offers, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class CategoryOffersView(APIView):
    """
    Get offers for specific category (Public endpoint)
    GET /api/offers/category/{category_id}/
    """
    permission_classes = [AllowAny]
    
    def get(self, request, category_id):
        """Get category offers"""
        today = timezone.now().date()
        
        # Check if category exists
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Category not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get active category offers that are currently valid
        offers = Offer.objects.filter(
            status=True,
            placement='category',
            category=category,
            valid_from__lte=today,
            valid_to__gte=today
        )
        
        serializer = OfferListSerializer(offers, many=True)
        return Response({
            'status': 'success',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


# ============================================================================
# AUDIT LOG VIEWS
# ============================================================================

class AuditLogListView(APIView):
    """
    GET /api/superadmin/audit-logs/
    Returns paginated audit logs for the admin dashboard.

    Query params:
      - category  : filter by category (KYC, ERP, Refund, System, Order, Category, Offer, Product)
      - search    : search across action, performed_by, target_entity, details
      - page      : page number (default 1)
      - page_size : results per page (default 20, max 100)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'code': '403',
                'type': 'auditLogs',
                'message': 'Only Super Admin can view audit logs'
            }, status=status.HTTP_403_FORBIDDEN)

        queryset = AuditLog.objects.all()

        # ── Filters ────────────────────────────────────────────────────────
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(action__icontains=search)
                | Q(performed_by__icontains=search)
                | Q(target_entity__icontains=search)
                | Q(details__icontains=search)
            )

        # ── Pagination ─────────────────────────────────────────────────────
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page = 1
            page_size = 20

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        logs = queryset[start:end]

        serializer = AuditLogSerializer(logs, many=True)

        return Response({
            'code': '200',
            'type': 'auditLogs',
            'message': f'Retrieved {len(serializer.data)} audit log(s)',
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size,
            },
            'data': serializer.data
        }, status=status.HTTP_200_OK)


# ==================== ORDER MANAGEMENT VIEWS ====================

class SuperAdminOrdersView(APIView):
    """
    API endpoint for superadmin to get all orders with items and payment info.
    GET /api/superadmin/orders/ - Get all orders with their line items
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all orders with items and payment details"""
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        # Query params for filtering
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search', '').strip()

        orders = SalesOrder.objects.prefetch_related(
            'items', 'payments'
        ).order_by('-created_at')

        # Filter by conversion status (maps to frontend status labels)
        if status_filter:
            status_map = {
                'Confirmed': {'ord_conversion_flag': True, 'dc_conversion_flag': False},
                'Dispatched': {'dc_conversion_flag': True},
                'Pending': {'ord_conversion_flag': False, 'dc_conversion_flag': False},
            }
            if status_filter in status_map:
                orders = orders.filter(**status_map[status_filter])

        # Search by order_id, patient_name, cust_name, or retailer shop_name (via KYC)
        if search:
            from django.db.models import Q
            # First get matching order_ids from direct order fields
            direct_matches = orders.filter(
                Q(order_id__icontains=search) |
                Q(patient_name__icontains=search) |
                Q(cust_name__icontains=search)
            )
            
            # Also search by retailer shop_name via KYC
            kyc_matches = KYC.objects.filter(shop_name__icontains=search).values_list('user_id', flat=True)
            shop_name_orders = SalesOrder.objects.filter(user_id__in=kyc_matches)
            
            # Combine both querysets
            order_ids = set(direct_matches.values_list('id', flat=True)) | set(shop_name_orders.values_list('id', flat=True))
            orders = SalesOrder.objects.filter(id__in=order_ids).order_by('-created_at')

        results = []
        for order in orders:
            # Determine order status
            payment = order.payments.first()
            payment_method = payment.get_payment_method_display() if payment else 'COD'
            payment_status = payment.status if payment else 'PENDING'

            if payment and payment.status == 'FAILED':
                order_status = 'Cancelled'
            elif order.dc_conversion_flag:
                order_status = 'Delivered'  # Matches Figma
            elif order.ord_conversion_flag:
                order_status = 'Confirmed'
            else:
                order_status = 'Pending'

            # Build items list for modal
            items_data = []
            for item in order.items.all():
                items_data.append({
                    'name': item.item_name or item.item_code,
                    'item_code': item.item_code,
                    'qty': item.total_loose_qty,
                    'mrp': float(item.sale_rate),
                    'total': float(item.item_total) if item.item_total else float(item.sale_rate) * item.total_loose_qty,
                    'batch_no': item.batch_no,
                })

            # Build timeline
            timeline = []
            timeline.append({
                'label': 'Created',
                'date': order.created_at.strftime('%Y-%m-%d %I:%M %p') if order.created_at else '',
                'status': 'completed'
            })
            if order.ord_conversion_flag:
                timeline.append({
                    'label': 'Confirmed',
                    'date': order.updated_at.strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })
            if order.dc_conversion_flag:
                timeline.append({
                    'label': 'Dispatched',
                    'date': order.updated_at.strftime('%Y-%m-%d %I:%M %p') if order.updated_at else '',
                    'status': 'completed'
                })
                
            # Get retailer shop name from KYC 
            retailer_shop_name = 'Unknown Retailer'
            retailer_id = order.store_id if order.store_id else 'RET001'
            retailer_user = None
            
            # Try to find the retailer user
            if order.user_id:
                try:
                    if order.user_id.isdigit():
                        retailer_user = get_user_model().objects.get(id=int(order.user_id))
                        # Get shop name from KYC
                        if hasattr(retailer_user, 'kyc') and retailer_user.kyc and retailer_user.kyc.shop_name:
                            retailer_shop_name = retailer_user.kyc.shop_name
                            if retailer_user.kyc.user_id:
                                retailer_id = retailer_user.kyc.user_id
                        # Fallback: use retailer username if no KYC shop_name
                        elif retailer_shop_name == 'Unknown Retailer':
                            retailer_shop_name = retailer_user.username
                except (ValueError, get_user_model().DoesNotExist):
                    pass
            
            # Final fallback: check if we can find KYC with c2_code
            if retailer_shop_name == 'Unknown Retailer' and order.c2_code:
                try:
                    kyc = KYC.objects.filter(user__c2_code=order.c2_code).first()
                    if kyc and kyc.shop_name:
                        retailer_shop_name = kyc.shop_name
                        retailer_id = kyc.user.c2_code or retailer_id
                except Exception:
                    pass

            results.append({
                'id': order.order_id,
                'retailer_id': retailer_id,
                'retailer': retailer_shop_name,
                'date': order.ord_date.strftime('%Y - %m - %d') if order.ord_date else '', # Figma format
                'items': order.items.count(),
                'total': str(order.order_total),
                'payment': payment_method,
                'payment_status': payment_status,
                'status': order_status,
                'erpRef': order.document_pk or f"{order.tran_prefix} - {order.tran_srno}" if order.tran_prefix else '',
                'detailedTimeline': timeline,
                'detailedItems': items_data,
            })

        return Response({
            'message': f'Found {len(results)} order(s)',
            'count': len(results),
            'results': results
        }, status=status.HTTP_200_OK)


class SuperAdminMarkCODDeliveredView(APIView):
    """
    API endpoint for superadmin to mark a COD order as delivered and payment collected.
    POST /api/superadmin/orders/cod-delivered/
    Payload: {"order_id": "..."}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        order_id = request.data.get('order_id')
        status_action = request.data.get('status', 'delivered') # 'paid', 'confirmed', 'delivered'
        
        if not order_id:
            return Response({'error': 'order_id is required in the payload'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = SalesOrder.objects.get(order_id=order_id)
        except SalesOrder.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Look for a COD payment associated with this order
        from payment.models import Payment
        payment = order.payments.filter(payment_method='COD').first()
        
        if not payment:
            return Response({'error': 'No COD payment found for this order'}, status=status.HTTP_400_BAD_REQUEST)

        if status_action in ['paid', 'confirmed', 'delivered'] and not payment.cod_collected:
            # Whenever they mark it as paid, confirmed or delivered, IF it's not yet collected, collect it
            pass

        if status_action == 'paid':
            if payment.cod_collected:
                return Response({'error': 'COD payment already marked as collected'}, status=status.HTTP_400_BAD_REQUEST)
            payment.cod_collected = True
            payment.cod_collected_at = timezone.now()
            payment.cod_collected_by = request.user.username
            payment.status = 'SUCCESS'
            payment.save()
            action_msg = 'COD Order Paid'
            log_details = f'Marked COD payment for Order "{order_id}" as paid/collected'

        elif status_action == 'confirmed':
            # Mark payment as collected if not already
            if not payment.cod_collected:
                payment.cod_collected = True
                payment.cod_collected_at = timezone.now()
                payment.cod_collected_by = request.user.username
                payment.status = 'SUCCESS'
                payment.save()
            
            # Update order to mark as confirmed
            order.ord_conversion_flag = True
            order.save()
            action_msg = 'COD Order Confirmed'
            log_details = f'Marked COD Order "{order_id}" as confirmed'

        else: # 'delivered'
            # Mark payment as collected if not already
            if not payment.cod_collected:
                payment.cod_collected = True
                payment.cod_collected_at = timezone.now()
                payment.cod_collected_by = request.user.username
                payment.status = 'SUCCESS'
                payment.save()
                
            # Update order to mark as delivered
            order.dc_conversion_flag = True
            order.ord_conversion_flag = True # Setting both for delivered
            order.save()
            action_msg = 'COD Order Delivered'
            log_details = f'Marked COD Order "{order_id}" as delivered and payment collected'

        # Audit log
        log_audit(
            action=action_msg,
            performed_by_user=request.user,
            target_entity=order_id,
            details=log_details,
            category='Order',
        )

        return Response({
            'success': True,
            'message': log_details + ' successfully'
        }, status=status.HTTP_200_OK)



class AdminNotificationListView(APIView):
    """
    List admin notifications
    GET /api/superadmin/notifications/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Only Super Admin can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
        
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        if unread_only:
            notifications = AdminNotification.objects.filter(is_read=False)
        else:
            notifications = AdminNotification.objects.all()
            
        serializer = AdminNotificationSerializer(notifications, many=True)
        return Response({
            'status': 'success',
            'unread_count': AdminNotification.objects.filter(is_read=False).count(),
            'data': serializer.data
        })

class AdminNotificationMarkReadView(APIView):
    """
    Mark notification as read
    POST /api/superadmin/notifications/<id>/mark-read/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Only Super Admin can access this endpoint'}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            notification = AdminNotification.objects.get(id=notification_id)
            notification.is_read = True
            notification.save()
            return Response({'status': 'success', 'message': 'Notification marked as read'})
        except AdminNotification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

# ==================== REPORTS & ANALYTICS VIEWS ====================

class ExcelExportMixin:
    def generate_excel(self, data, report_type):
        if not data:
            return Response({'error': 'No data available to export'}, status=status.HTTP_400_BAD_REQUEST)
            
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = report_type.capitalize()

        # Write headers
        headers = list(data[0].keys())
        sheet.append(headers)

        # Write rows
        for row in data:
            sheet.append([str(val) if val is not None else '' for val in row.values()])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{report_type}.xlsx"'
        return response

class ReportSummaryView(APIView):
    """
    MTD cards data for Reports page.
    GET /api/superadmin/reports/summary/?start_date=...&end_date=...
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        # ── Date range (default: current month MTD) ───────────────────────────
        start_date_str = request.query_params.get('start_date')
        end_date_str   = request.query_params.get('end_date')

        if start_date_str and end_date_str:
            start_date = parse_date(start_date_str)
            end_date   = parse_date(end_date_str)
            if not start_date or not end_date:
                return Response(
                    {'error': 'Invalid date format. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            today      = timezone.now().date()
            start_date = today.replace(day=1)   # 1st of this month
            end_date   = today                  # today (MTD)

        # ── MTD order queryset ────────────────────────────────────────────────
        orders = SalesOrder.objects.filter(
            ord_date__gte=start_date,
            ord_date__lte=end_date
        )

        # 1. Total Orders (MTD)
        total_orders = orders.count()

        # 2. Total Revenue (MTD) – sum of order_total
        total_revenue = float(orders.aggregate(total=Sum('order_total'))['total'] or 0.0)

        # 3. Avg Order Value – revenue ÷ orders (avoids Django Avg() skipping NULL rows)
        avg_order_value = round(total_revenue / total_orders, 2) if total_orders > 0 else 0.0

        # ── Active Retailers in period ────────────────────────────────────────
        valid_retailer_ids = set(
            str(uid) for uid in User.objects.filter(role='RETAILER').values_list('id', flat=True)
        )
        active_retailers = len(set(
            uid for uid in orders.values_list('user_id', flat=True).distinct()
            if uid and uid in valid_retailer_ids
        ))

        # ── Previous month (full calendar month before start_date) ────────────
        prev_end   = start_date - timedelta(days=1)   # last day of previous month
        prev_start = prev_end.replace(day=1)          # 1st day of previous month

        prev_orders       = SalesOrder.objects.filter(ord_date__gte=prev_start, ord_date__lte=prev_end)
        prev_total_orders = prev_orders.count()
        prev_revenue      = float(prev_orders.aggregate(total=Sum('order_total'))['total'] or 0.0)
        prev_avg          = round(prev_revenue / prev_total_orders, 2) if prev_total_orders > 0 else 0.0

        def calc_change_pct(curr, prev_val):
            if prev_val > 0:
                return round((curr - prev_val) / prev_val * 100, 1)
            return 100.0 if curr > 0 else 0.0

        return Response({
            'success': True,
            'period': {
                'start_date': str(start_date),
                'end_date':   str(end_date),
            },
            'data': {
                'total_revenue':               total_revenue,
                'total_orders':                total_orders,
                'avg_order_value':             avg_order_value,
                'active_retailers':            active_retailers,
                'revenue_change_percentage':   calc_change_pct(total_revenue,   prev_revenue),
                'orders_change_percentage':    calc_change_pct(total_orders,    prev_total_orders),
                'avg_order_change_percentage': calc_change_pct(avg_order_value, prev_avg),
            }
        })

class KYCStatusReportView(APIView, ExcelExportMixin):
    """
    KYC approval/rejection statistics and record list.
    GET /api/superadmin/reports/kyc/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = KYC.objects.all().order_by('-submitted_at')
        if start_date and end_date:
            queryset = queryset.filter(submitted_at__date__range=[start_date, end_date])

        summary = queryset.values('status').annotate(count=Count('id'))
        report_data = []
        for item in queryset[:100]: # Limit for list view
            report_data.append({
                'retailer': item.user.username,
                'shop_name': item.shop_name,
                'status': item.status,
                'date': item.submitted_at.strftime('%Y-%m-%d'),
                'approved_at': item.approved_at.strftime('%Y-%m-%d') if item.approved_at else 'N/A'
            })

        if request.query_params.get('export') == 'excel':
            return self.generate_excel(report_data, 'kyc_status_report')

        return Response({
            'success': True,
            'summary': list(summary),
            'data': report_data
        })

class OrderReportView(APIView, ExcelExportMixin):
    """
    Detailed list of orders with specific columns for reports.
    GET /api/superadmin/reports/orders/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        search = request.query_params.get('search', '')

        orders = SalesOrder.objects.all().order_by('-ord_date')
        if start_date and end_date:
            orders = orders.filter(ord_date__range=[start_date, end_date])
        
        if search:
            orders = orders.filter(
                Q(order_id__icontains=search) | 
                Q(cust_name__icontains=search)
            )

        data = []
        for order in orders:
            data.append({
                'order_id': order.order_id,
                'retailer': order.cust_name or order.patient_name,
                'date': order.ord_date.strftime('%Y-%m-%d') if order.ord_date else '',
                'items': order.items.count(),
                'total': float(order.order_total),
                'status': 'Delivered' if order.dc_conversion_flag else ('Confirmed' if order.ord_conversion_flag else 'Pending'),
                'erp_ref': order.document_pk or 'N/A'
            })

        if request.query_params.get('export') == 'excel':
            return self.generate_excel(data, 'order_report')

        return Response({
            'success': True,
            'count': len(data),
            'data': data
        })

class RetailerActivityReportView(APIView, ExcelExportMixin):
    """
    Retailer-wise ordering patterns.
    GET /api/superadmin/reports/retailer-activity/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        # Aggregate users by their orders
        activity = SalesOrder.objects.values('user_id', 'cust_name').annotate(
            order_count=Count('id'),
            total_spent=Sum('order_total'),
            last_order=Max('ord_date')
        ).order_by('-total_spent')

        activity_list = list(activity)
        if request.query_params.get('export') == 'excel':
            return self.generate_excel(activity_list, 'retailer_activity_report')

        return Response({
            'success': True,
            'data': activity_list
        })

class RevenueReportView(APIView, ExcelExportMixin):
    """
    Daily revenue trends for line charts.
    GET /api/superadmin/reports/revenue/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        today = timezone.now().date()
        start = today - timedelta(days=30)
        
        revenue_data = SalesOrder.objects.filter(ord_date__range=[start, today]) \
            .values('ord_date') \
            .annotate(revenue=Sum('order_total')) \
            .order_by('ord_date')

        revenue_list = list(revenue_data)
        if request.query_params.get('export') == 'excel':
            return self.generate_excel(revenue_list, 'revenue_report')

        return Response({
            'success': True,
            'data': revenue_list
        })


class RefundTrendsView(APIView):
    """
    Refund/Credit Note trends by month and year.
    GET /api/superadmin/reports/refund-trends/?view=monthly&year=2026
    
    Query Parameters:
    - view: 'monthly' (current year or specified year) or 'yearly' (last N years)
    - year: Year for monthly view (default: current year)
    - months: Number of months for monthly view (default: 12)
    - years: Number of years for yearly view (default: 3)
    
    Returns:
    - Monthly view: [{"month": "October", "count": 35, "amount": 5000.50}, ...]
    - Yearly view: [{"year": 2024, "count": 180, "amount": 25000.00}, ...]
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({
                'error': 'Only Super Admin can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)

        view_type = request.query_params.get('view', 'monthly').lower()
        
        if view_type == 'monthly':
            return self._get_monthly_trends(request)
        elif view_type == 'yearly':
            return self._get_yearly_trends(request)
        else:
            return Response({
                'error': "Invalid view. Must be 'monthly' or 'yearly'"
            }, status=status.HTTP_400_BAD_REQUEST)

    def _get_monthly_trends(self, request):
        """Get monthly refund trends"""
        try:
            year = int(request.query_params.get('year', timezone.now().year))
            months = int(request.query_params.get('months', 12))
        except ValueError:
            return Response({
                'error': 'Invalid year or months parameter'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30 * months)
        
        # Get credit notes grouped by month
        monthly_data = CreditNote.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('credit_note_id'),
            amount=Sum('amount', output_field=DecimalField())
        ).order_by('month')
        
        # Format response with month names
        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']
        
        trends = []
        for item in monthly_data:
            if item['month']:
                month_index = item['month'].month - 1
                month_name = month_names[month_index]
                month_short = month_names[month_index][:3]
                
                trends.append({
                    'month': month_name,
                    'month_short': month_short,
                    'month_num': item['month'].month,
                    'year': item['month'].year,
                    'count': item['count'] or 0,
                    'amount': float(item['amount'] or 0)
                })
        
        return Response({
            'success': True,
            'view': 'monthly',
            'year_displayed': year,
            'total_months': len(trends),
            'trends': trends,
            'summary': {
                'total_refunds': sum(t['count'] for t in trends),
                'total_amount': sum(t['amount'] for t in trends)
            }
        }, status=status.HTTP_200_OK)

    def _get_yearly_trends(self, request):
        """Get yearly refund trends"""
        try:
            num_years = int(request.query_params.get('years', 3))
        except ValueError:
            return Response({
                'error': 'Invalid years parameter'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365 * num_years)
        
        # Get credit notes grouped by year
        yearly_data = CreditNote.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            year=TruncYear('created_at')
        ).values('year').annotate(
            count=Count('credit_note_id'),
            amount=Sum('amount', output_field=DecimalField())
        ).order_by('year')
        
        trends = []
        for item in yearly_data:
            if item['year']:
                trends.append({
                    'year': item['year'].year,
                    'count': item['count'] or 0,
                    'amount': float(item['amount'] or 0)
                })
        
        return Response({
            'success': True,
            'view': 'yearly',
            'years_displayed': num_years,
            'total_years': len(trends),
            'trends': trends,
            'summary': {
                'total_refunds': sum(t['count'] for t in trends),
                'total_amount': sum(t['amount'] for t in trends)
            }
        }, status=status.HTTP_200_OK)


class DailyVolumeGraphView(APIView):
    """
    API endpoint for getting daily volume graph data and top statistics.
    GET /api/superadmin/dashboard/daily-volume/?days=7
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'SUPERADMIN':
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

        try:
            days = int(request.query_params.get('days', 7))
        except ValueError:
            days = 7

        now = timezone.now()
        start_date = (now - timedelta(days=days-1)).date()
        today_date = now.date()

        # Gather daily order counts and sales
        daily_stats = SalesOrder.objects.filter(ord_date__range=[start_date, today_date]) \
            .values('ord_date') \
            .annotate(
                order_count=Count('id'),
                total_sales=Sum('order_total')
            ) \
            .order_by('ord_date')

        # Convert to dictionary for easy filling of missing days
        stats_dict = {item['ord_date']: {'orders': item['order_count'], 'sales': float(item['total_sales'] or 0)} for item in daily_stats}

        graph_data = []
        max_orders = {'date': None, 'count': 0}
        max_sales = {'date': None, 'amount': 0.0}

        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_data = stats_dict.get(current_date, {'orders': 0, 'sales': 0.0})
            
            graph_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'display_date': current_date.strftime('%b %d'),
                'orders': day_data['orders'],
                'sales': day_data['sales']
            })

            if day_data['orders'] > max_orders['count']:
                max_orders = {'date': current_date.strftime('%Y-%m-%d'), 'count': day_data['orders']}
            if day_data['sales'] > max_sales['amount']:
                max_sales = {'date': current_date.strftime('%Y-%m-%d'), 'amount': day_data['sales']}

        # Get top selling product for this period
        top_product_entry = SalesOrderItem.objects.filter(
            order_id__ord_date__range=[start_date, today_date]
        ).values('item_name').annotate(
            total_qty=Sum('total_loose_qty')
        ).order_by('-total_qty').first()

        top_selling_product = None
        if top_product_entry:
            top_selling_product = {
                'name': top_product_entry['item_name'],
                'quantity': float(top_product_entry['total_qty'] or 0)
            }

        return Response({
            'success': True,
            'summary': {
                'period_days': days,
                'max_orders_day': max_orders,
                'max_sales_day': max_sales,
                'top_selling_product': top_selling_product
            },
            'graph_data': graph_data
        })
