"""
Wallet service for managing retailer wallet credits and debits
"""
from django.db import transaction
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def credit_wallet(retailer, amount, source, credit_note=None, order=None, description=''):
    """
    Add money to retailer wallet
    Called after credit note approval
    
    Args:
        retailer: CustomUser instance (retailer)
        amount: Decimal amount to credit
        source: String - SOURCE_CHOICES value
        credit_note: CreditNote instance (optional)
        order: SalesOrder instance (optional)
        description: String description of transaction
    
    Returns:
        dict with success status and new balance
    """
    from .models import RetailerWallet, WalletTransaction
    
    # Ensure amount is Decimal
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except Exception as e:
            return {'success': False, 'error': f'Invalid amount format: {str(e)}'}

    try:
        with transaction.atomic():
            # Get or create wallet
            wallet, _ = RetailerWallet.objects.get_or_create(retailer=retailer)
            
            # Add balance
            wallet.balance += amount
            wallet.save()
            
            # Log transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                source=source,
                amount=amount,
                credit_note=credit_note,
                order=order,
                description=description,
                closing_balance=wallet.balance
            )
            
            logger.info(
                f"[WALLET_CREDIT] Retailer: {retailer.username} | "
                f"Amount: ₹{amount} | "
                f"New Balance: ₹{wallet.balance} | "
                f"Source: {source}"
            )
            
            return {
                'success': True,
                'new_balance': wallet.balance
            }
    
    except Exception as e:
        logger.error(f"[WALLET_ERROR] Failed to credit wallet: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def debit_wallet(retailer, amount, source, order=None, description=''):
    """
    Deduct money from retailer wallet
    Called when wallet balance used during order payment
    
    Args:
        retailer: CustomUser instance (retailer)
        amount: Decimal amount to debit
        source: String - SOURCE_CHOICES value
        order: SalesOrder instance (optional)
        description: String description of transaction
    
    Returns:
        dict with success status and new balance, or error message
    """
    from .models import RetailerWallet, WalletTransaction
    
    # Ensure amount is Decimal
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except Exception as e:
            return {'success': False, 'error': f'Invalid amount format: {str(e)}'}

    try:
        with transaction.atomic():
            wallet, _ = RetailerWallet.objects.get_or_create(retailer=retailer)
            
            # Check sufficient balance
            if wallet.balance < amount:
                return {
                    'success': False,
                    'error': f'Insufficient balance. Available: ₹{wallet.balance}'
                }
            
            # Deduct balance
            wallet.balance -= amount
            wallet.save()
            
            # Log transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='DEBIT',
                source=source,
                amount=amount,
                order=order,
                description=description,
                closing_balance=wallet.balance
            )
            
            logger.info(
                f"[WALLET_DEBIT] Retailer: {retailer.username} | "
                f"Amount: ₹{amount} | "
                f"New Balance: ₹{wallet.balance}"
            )
            
            return {
                'success': True,
                'new_balance': wallet.balance
            }
    
    except Exception as e:
        logger.error(f"[WALLET_ERROR] Failed to debit wallet: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_wallet_balance(retailer):
    """
    Get current wallet balance for a retailer
    
    Args:
        retailer: CustomUser instance (retailer)
    
    Returns:
        Decimal balance amount
    """
    from .models import RetailerWallet
    
    wallet, _ = RetailerWallet.objects.get_or_create(retailer=retailer)
    return wallet.balance
