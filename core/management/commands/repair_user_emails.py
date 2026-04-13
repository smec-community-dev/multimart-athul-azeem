from collections import defaultdict

from django.core.management.base import BaseCommand

from core.models import User


class Command(BaseCommand):
    help = "Fix duplicate users by normalizing email and deactivating duplicate rows."

    def handle(self, *args, **options):
        grouped = defaultdict(list)
        for user in User.objects.all().order_by("id"):
            if user.email:
                grouped[user.email.strip().lower()].append(user)

        fixed = 0
        for email, users in grouped.items():
            if len(users) <= 1:
                continue

            primary = users[0]
            if primary.email != email:
                primary.email = email
                primary.save(update_fields=["email"])

            for duplicate in users[1:]:
                duplicate.is_active = False
                duplicate.email = f"archived+{duplicate.id}@local.invalid"
                duplicate.username = f"{duplicate.username}_archived_{duplicate.id}"
                duplicate.save(update_fields=["is_active", "email", "username"])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f"User repair finished. Duplicates archived: {fixed}"))
