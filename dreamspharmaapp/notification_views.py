"""
Retailer Notification API Views
GET-only endpoints for retrieving notifications about new offers/discounts
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from .models import RetailerNotification
from .serializers import RetailerNotificationListSerializer, RetailerNotificationSerializer


class RetailerNotificationsListView(APIView):
    """
    GET /api/retailer-notifications/
    
    Get all notifications for the authenticated retailer (paginated)
    Requires JWT authentication
    
    Query Parameters:
    - limit: Number of results (default: 20)
    - offset: Pagination offset (default: 0)
    - unread_only: Filter to unread notifications (true/false)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get notifications for authenticated retailer"""
        try:
            # Use authenticated user
            user = request.user
            user_id = user.id
            
            # Get pagination params
            limit = int(request.query_params.get('limit', 20))
            offset = int(request.query_params.get('offset', 0))
            unread_only = request.query_params.get('unread_only', '').lower() == 'true'
            
            # Get notifications
            notifications = RetailerNotification.objects.filter(retailer_id=user_id)
            
            # Filter unread if requested
            if unread_only:
                notifications = notifications.filter(is_read=False)
            
            # Get total count
            total_count = notifications.count()
            
            # Apply pagination
            notifications = notifications[offset:offset + limit]
            
            serializer = RetailerNotificationListSerializer(notifications, many=True)
            
            return Response({
                'status': 'success',
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'count': len(notifications),
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetailerNotificationDetailView(APIView):
    """
    GET /api/retailer-notifications/{notification_id}/
    PUT /api/retailer-notifications/{notification_id}/ (mark as read)
    DELETE /api/retailer-notifications/{notification_id}/
    
    Get, update, or delete a specific notification
    PUT and DELETE require JWT authentication
    """
    permission_classes = [AllowAny]
    
    def get(self, request, notification_id):
        """Get notification details"""
        try:
            notification = RetailerNotification.objects.get(notification_id=notification_id)
            serializer = RetailerNotificationSerializer(notification)
            
            return Response({
                'status': 'success',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except RetailerNotification.DoesNotExist:
            return Response({
                'status': 'error',
                'message': f'Notification {notification_id} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, notification_id):
        """Mark notification as read - requires JWT authentication"""
        try:
            # Get authenticated user
            if not request.user.is_authenticated:
                return Response({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user_id = request.user.id
            
            # Get the notification
            try:
                notification = RetailerNotification.objects.get(notification_id=notification_id)
            except RetailerNotification.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': f'Notification {notification_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify ownership - user_id must match the notification's retailer
            if str(notification.retailer_id) != str(user_id):
                return Response({
                    'status': 'error',
                    'message': 'You can only mark your own notifications as read'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Mark as read
            notification.mark_as_read()
            
            serializer = RetailerNotificationSerializer(notification)
            
            return Response({
                'status': 'success',
                'message': 'Notification marked as read',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, notification_id):
        """Delete a notification - requires JWT authentication"""
        try:
            # Get authenticated user
            if not request.user.is_authenticated:
                return Response({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user_id = request.user.id
            
            # Get the notification
            try:
                notification = RetailerNotification.objects.get(notification_id=notification_id)
            except RetailerNotification.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': f'Notification {notification_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Verify ownership - user_id must match the notification's retailer
            if str(notification.retailer_id) != str(user_id):
                return Response({
                    'status': 'error',
                    'message': 'You can only delete your own notifications'
                }, status=status.HTTP_403_FORBIDDEN)
            
            notification.delete()
            
            return Response({
                'status': 'success',
                'message': 'Notification deleted'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetailerNotificationCountView(APIView):
    """
    GET /api/retailer-notifications/count/
    
    Get count of unread notifications for authenticated retailer
    Requires JWT authentication
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get unread notification count for authenticated user"""
        try:
            user_id = request.user.id
            
            unread_count = RetailerNotification.objects.filter(
                retailer_id=user_id,
                is_read=False
            ).count()
            
            total_count = RetailerNotification.objects.filter(
                retailer_id=user_id
            ).count()
            
            return Response({
                'status': 'success',
                'unread_count': unread_count,
                'total_count': total_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def send_offer_notification_to_all_retailers(offer):
    """
    Helper function to create notifications for all retailers when offer is created
    Called from OfferListCreateView.post()
    """
    try:
        from .models import CustomUser
        
        # Get all active retailers (APPROVED or LOGIN_ENABLED status)
        retailers = CustomUser.objects.filter(role='RETAILER', status__in=['APPROVED', 'LOGIN_ENABLED'])
        
        # Build notification message safely (handle null category)
        if offer.category:
            message = f"Get {offer.discount_percentage}% discount on {offer.category.name} products"
        else:
            message = f"Check out: {offer.title} - {offer.discount_percentage}% discount"
        
        # Prepare notifications
        notifications = []
        for retailer in retailers:
            notification = RetailerNotification(
                retailer=retailer,
                title=f"New Offer: {offer.title}",
                message=message,
                offer=offer,
                icon_url=offer.banner_image.url if offer.banner_image else None,
                notification_type='OFFER'  # Add notification type
            )
            notifications.append(notification)
        
        # Bulk create
        if notifications:
            RetailerNotification.objects.bulk_create(notifications)
            return {
                'success': True,
                'count': len(notifications),
                'message': f'Notifications sent to {len(notifications)} retailers'
            }
        else:
            return {
                'success': True,
                'count': 0,
                'message': 'No approved retailers to notify'
            }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error creating notifications: {str(e)}'
        }
