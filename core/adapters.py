from urllib.parse import urlparse

import requests
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """
        Social login redirect. Normal username/password login uses normal_login_view().
        """
        user = request.user
        if user.is_authenticated and user.is_superuser:
            return reverse("admin_panel:admin_dashboard")

        if user.is_authenticated and SocialAccount.objects.filter(user=user).exists():
            return "/choose-role/"

        return reverse("user:user_home")

    def get_signup_redirect_url(self, request):
        """
        ONLY for social signup (Google) → choose-role
        """
        return "/choose-role/"

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Handles Google sign-in safely:
    - connect by email to avoid duplicate users
    - keep default role
    - sync name and profile image when available
    """

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").strip().lower()
        if not email:
            return

        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # Link Google account to existing user instead of creating duplicate.
        sociallogin.connect(request, existing_user)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if not user.role:
            user.role = "user"
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)

        if not user.role:
            user.role = "user"

        extra = sociallogin.account.extra_data or {}
        user.first_name = user.first_name or extra.get("given_name", "")
        user.last_name = user.last_name or extra.get("family_name", "")

        picture_url = extra.get("picture")
        if picture_url and not user.profile_image:
            try:
                response = requests.get(picture_url, timeout=5)
                if response.ok and response.content:
                    ext = ".jpg"
                    parsed = urlparse(picture_url).path
                    if "." in parsed:
                        ext = parsed[parsed.rfind(".") :]
                        if len(ext) > 5:
                            ext = ".jpg"
                    filename = f"google_{user.username}{ext}"
                    user.profile_image.save(filename, ContentFile(response.content), save=False)
            except Exception:
                pass

        user.save()
        return user