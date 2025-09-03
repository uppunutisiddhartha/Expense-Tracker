from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean expired sessions from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about deleted sessions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired sessions found to delete')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} expired sessions'
                )
            )
            if verbose:
                for session in expired_sessions[:5]:
                    self.stdout.write(f"  - {session.session_key} (expires: {session.expire_date})")
        else:
            deleted_count, _ = expired_sessions.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} expired sessions'
                )
            )
            if verbose:
                self.stdout.write("Expired sessions have been cleaned up") 
from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone

class Command(BaseCommand):
    help = 'Clean expired sessions from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about deleted sessions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired sessions found to delete')
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} expired sessions'
                )
            )
            if verbose:
                for session in expired_sessions[:5]:
                    self.stdout.write(f"  - {session.session_key} (expires: {session.expire_date})")
        else:
            deleted_count, _ = expired_sessions.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} expired sessions'
                )
            )
            if verbose:
                self.stdout.write("Expired sessions have been cleaned up")