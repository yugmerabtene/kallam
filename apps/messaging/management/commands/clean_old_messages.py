"""
Politique de rétention des messages privés.

Usage :
    python manage.py clean_old_messages            # supprime messages > 90 jours
    python manage.py clean_old_messages --days=30  # supprime messages > 30 jours
    python manage.py clean_old_messages --dry-run  # simule sans supprimer
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.messaging.models import Conversation, Message


class Command(BaseCommand):
    help = "Supprime les messages privés plus vieux que N jours (défaut: 90)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Âge maximal des messages en jours (défaut: 90).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait supprimé sans supprimer.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        old_messages = Message.objects.filter(created_at__lt=cutoff)
        count = old_messages.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] {count} message(s) seraient supprimés "
                    f"(antérieurs au {cutoff.date()})."
                )
            )
            return

        old_messages.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"{count} message(s) supprimés (antérieurs au {cutoff.date()})."
            )
        )

        empty_convs = Conversation.objects.filter(messages__isnull=True)
        empty_count = empty_convs.count()
        empty_convs.delete()
        if empty_count:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{empty_count} conversation(s) vide(s) supprimée(s)."
                )
            )
