from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        """
        ONLY for social auth (Google) → choose-role
        Normal login redirects are handled in normal_login_view()
        """
        # Check if this is a social login
        if request.user.is_authenticated:
            # If user has social account (Google), go to choose-role
            if SocialAccount.objects.filter(user=request.user).exists():
                return "/choose-role/"

        # This shouldn't be reached for normal login
        return "/choose-role/"

    def get_signup_redirect_url(self, request):
        """
        ONLY for social signup (Google) → choose-role
        """
        return "/choose-role/"

    def pre_social_login(self, request, sociallogin):
        """
        If this email already exists → connect & login.
        If not, allow allauth to create a new user.
        """
        email = sociallogin.user.email
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
        except User.DoesNotExist:
            # new user, normal social signup
            return

        # If already linked with this provider → just log them in
        if SocialAccount.objects.filter(
                user=existing_user,
                provider=sociallogin.account.provider
        ).exists():
            sociallogin.connect(request, existing_user)
            return

        # Email exists but not linked → block duplicate social signup
        messages.error(request, "This email is already registered. Please login instead.")
        raise ImmediateHttpResponse(redirect("/login/?error=email_exists"))

    def save_user(self, request, user, form, commit=True):
        """
        When Google creates a user, set default role = 'user'
        They can change it later via choose-role
        """
        user = super().save_user(request, user, form, commit=False)

        # Set default role for social auth users
        if not user.role:
            user.role = "user"

        if commit:
            user.save()

        return user

