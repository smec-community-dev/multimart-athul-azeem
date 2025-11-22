from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        return "/choose-role/"

    def get_signup_redirect_url(self, request):
        return "/choose-role/"

    def pre_social_login(self, request, sociallogin):
        """Block Google signup if email already exists."""
        email = sociallogin.user.email
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        # If already linked with Google → login direct
        if SocialAccount.objects.filter(
            user=existing_user,
            provider=sociallogin.account.provider
        ).exists():
            sociallogin.connect(request, existing_user)
            return

        # Email exists but NOT linked → Block signup
        messages.error(request, "This email is already registered. Please login.")
        raise ImmediateHttpResponse(redirect("/login/?error=email_exists"))

    def save_user(self, request, user, form, commit=True):
        """
        Prevent Google from overwriting existing names.
        """
        old_first = user.first_name
        old_last = user.last_name

        user = super().save_user(request, user, form, commit=False)

        if old_first:
            user.first_name = old_first
        if old_last:
            user.last_name = old_last

        if commit:
            user.save()

        return user
