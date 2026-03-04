from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings


def send_kyc_approval_email(user, kyc):
    """
    Send KYC approval email to the retailer
    
    Args:
        user: CustomUser instance (retailer)
        kyc: KYC instance
    """
    try:
        subject = 'KYC Approval - Welcome to Dream Pharma!'
        
        # Prepare email context
        context = {
            'retailer_name': user.first_name or user.username,
            'shop_name': kyc.shop_name,
            'approval_date': kyc.approved_at.strftime('%d-%m-%Y') if kyc.approved_at else 'N/A',
            'email': user.email,
        }
        
        # Create HTML email body
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #007bff; padding: 20px; color: white; text-align: center;">
                        <h1 style="margin: 0;">KYC Approved!</h1>
                    </div>
                    <div style="padding: 20px;">
                        <p>Dear {context['retailer_name']},</p>
                        
                        <p>Congratulations! Your KYC (Know Your Customer) verification has been <strong>approved</strong>.</p>
                        
                        <div style="background-color: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Approval Details:</strong></p>
                            <ul style="list-style-type: none; padding: 0;">
                                <li><strong>Shop Name:</strong> {context['shop_name']}</li>
                                <li><strong>Approval Date:</strong> {context['approval_date']}</li>
                                <li><strong>Registered Email:</strong> {context['email']}</li>
                            </ul>
                        </div>
                        
                        <p>You can now proceed with your account activation. Your account will be fully activated shortly.</p>
                        
                        <p>If you have any questions, please contact our support team.</p>
                        
                        <p style="margin-top: 30px; color: #666; font-size: 12px;">
                            <strong>Dream Pharma</strong><br>
                            This is an automated email. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=f"Dear {context['retailer_name']},\n\nCongratulations! Your KYC verification has been approved.\n\nShop Name: {context['shop_name']}\nApproval Date: {context['approval_date']}\n\nBest regards,\nDream Pharma Team",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending KYC approval email to {user.email}: {str(e)}")
        return False


def send_kyc_rejection_email(user, kyc, rejection_reason):
    """
    Send KYC rejection email to the retailer with reason
    
    Args:
        user: CustomUser instance (retailer)
        kyc: KYC instance
        rejection_reason: Reason for rejection
    """
    try:
        subject = 'KYC Rejection - Action Required'
        
        # Prepare email context
        context = {
            'retailer_name': user.first_name or user.username,
            'shop_name': kyc.shop_name,
            'rejection_reason': rejection_reason,
            'email': user.email,
        }
        
        # Create HTML email body
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #dc3545; padding: 20px; color: white; text-align: center;">
                        <h1 style="margin: 0;">KYC Rejected</h1>
                    </div>
                    <div style="padding: 20px;">
                        <p>Dear {context['retailer_name']},</p>
                        
                        <p>We regret to inform you that your KYC (Know Your Customer) verification has been <strong>rejected</strong>.</p>
                        
                        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                            <p><strong>Rejection Reason:</strong></p>
                            <p style="color: #721c24; margin: 10px 0 0 0;">{context['rejection_reason']}</p>
                        </div>
                        
                        <p><strong>What Next?</strong></p>
                        <ol>
                            <li>Review the rejection reason mentioned above</li>
                            <li>Collect/correct your documents as per the feedback</li>
                            <li>Resubmit your KYC with updated documents</li>
                        </ol>
                        
                        <p>If you have questions about the rejection, please contact our support team for further assistance.</p>
                        
                        <p style="margin-top: 30px; color: #666; font-size: 12px;">
                            <strong>Dream Pharma</strong><br>
                            This is an automated email. Please do not reply to this email.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=f"Dear {context['retailer_name']},\n\nYour KYC verification has been rejected.\n\nReason: {context['rejection_reason']}\n\nPlease contact our support team for further assistance.\n\nBest regards,\nDream Pharma Team",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending KYC rejection email to {user.email}: {str(e)}")
        return False
