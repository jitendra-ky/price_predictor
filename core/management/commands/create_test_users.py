from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test users for demonstrating the paid membership feature'

    def handle(self, *args, **options):
        # Create Free user
        free_user, created = User.objects.get_or_create(
            username='freeuser',
            defaults={
                'email': 'free@example.com',
                'first_name': 'Free',
                'last_name': 'User'
            }
        )
        if created:
            free_user.set_password('testpass123')
            free_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created free user: {free_user.username}'))
        
        # Ensure free user has profile (should be auto-created)
        profile, created = UserProfile.objects.get_or_create(user=free_user)
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created profile for free user'))
        
        # Create Pro user
        pro_user, created = User.objects.get_or_create(
            username='prouser',
            defaults={
                'email': 'pro@example.com',
                'first_name': 'Pro',
                'last_name': 'User'
            }
        )
        if created:
            pro_user.set_password('testpass123')
            pro_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created pro user: {pro_user.username}'))
        
        # Set pro user as Pro subscriber
        pro_profile, created = UserProfile.objects.get_or_create(user=pro_user)
        if not pro_profile.is_pro:
            pro_profile.is_pro = True
            pro_profile.save()
            self.stdout.write(self.style.SUCCESS(f'Set {pro_user.username} as Pro subscriber'))
        
        self.stdout.write(
            self.style.SUCCESS(
                '\nTest users created successfully!\n'
                'Free User: freeuser / testpass123 (5 predictions/day)\n'
                'Pro User: prouser / testpass123 (unlimited predictions)\n'
            )
        )
        
        # Display current status
        self.stdout.write('\nCurrent user status:')
        for user in [free_user, pro_user]:
            profile = user.userprofile
            self.stdout.write(
                f'{user.username}: is_pro={profile.is_pro}, '
                f'quota={profile.get_daily_quota()}, '
                f'remaining={profile.get_remaining_predictions()}'
            )
