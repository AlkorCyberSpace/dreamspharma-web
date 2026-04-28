"""
Management command to auto-inactivate expired offers
Usage: python manage.py inactivate_expired_offers
Run as a cron job daily at midnight
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from dreamspharmaapp.models import Offer


class Command(BaseCommand):
    help = 'Auto-inactivate offers that have passed their valid_to date'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Find active offers that have expired
        expired_offers = Offer.objects.filter(
            status=True,
            valid_to__lt=today
        )
        
        count = expired_offers.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ No expired offers found')
            )
            return
        
        # Inactivate them
        updated = expired_offers.update(status=False)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Successfully inactivated {updated} expired offer(s) as of {today}'
            )
        )
        
        # Log the details
        for offer in expired_offers:
            self.stdout.write(
                f"   - {offer.offer_id}: {offer.title} (expired: {offer.valid_to})"
            )
