"""
OTP-based forgot password (email code, 5-minute expiry).
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import PasswordResetOTP

User = get_user_model()

SESSION_USER_KEY = "password_reset_user_id"
SESSION_VERIFIED_KEY = "password_reset_otp_verified"
OTP_EXPIRY = timedelta(minutes=5)


def _random_six_digit_otp() -> str:
    return f"{secrets.randbelow(900000) + 100000}"


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect("user:user_home")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, "auth/forgot_password.html")

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            messages.error(request, "No account is registered with that email address.")
            return render(request, "auth/forgot_password.html")

        # One active flow per user: remove old codes before issuing a new one
        PasswordResetOTP.objects.filter(user=user).delete()
        otp = _random_six_digit_otp()
        PasswordResetOTP.objects.create(user=user, otp=otp)

        subject = "MultiMart — password reset code"
        body = (
            f"Your MultiMart password reset code is: {otp}\n\n"
            "This code expires in 5 minutes. If you did not request this, you can ignore this email."
        )
        try:
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            messages.error(
                request,
                "We could not send the email right now. Please try again in a few minutes.",
            )
            PasswordResetOTP.objects.filter(user=user).delete()
            return render(request, "auth/forgot_password.html")

        request.session[SESSION_USER_KEY] = user.pk
        request.session[SESSION_VERIFIED_KEY] = False
        messages.success(request, "We sent a 6-digit code to your email.")
        return redirect("admin_panel:verify_otp")

    return render(request, "auth/forgot_password.html")


def verify_otp_view(request):
    if request.user.is_authenticated:
        return redirect("user:user_home")

    uid = request.session.get(SESSION_USER_KEY)
    if not uid:
        messages.error(request, "Start again from the forgot password page.")
        return redirect("admin_panel:forgot_password")

    if request.method == "POST":
        code = (request.POST.get("otp") or "").strip()
        if len(code) != 6 or not code.isdigit():
            messages.error(request, "Enter the 6-digit code from your email.")
            return render(request, "auth/verify_otp.html")

        user = User.objects.filter(pk=uid).first()
        if user is None:
            request.session.pop(SESSION_USER_KEY, None)
            request.session.pop(SESSION_VERIFIED_KEY, None)
            return redirect("admin_panel:forgot_password")

        latest = (
            PasswordResetOTP.objects.filter(user=user).order_by("-created_at").first()
        )
        if latest is None or latest.otp != code:
            messages.error(request, "That code is not valid. Check your email and try again.")
            return render(request, "auth/verify_otp.html")

        if timezone.now() - latest.created_at > OTP_EXPIRY:
            messages.error(request, "This code has expired. Request a new one.")
            PasswordResetOTP.objects.filter(user=user).delete()
            request.session.pop(SESSION_USER_KEY, None)
            request.session.pop(SESSION_VERIFIED_KEY, None)
            return redirect("admin_panel:forgot_password")

        request.session[SESSION_VERIFIED_KEY] = True
        messages.success(request, "Code verified. Enter your new password.")
        return redirect("admin_panel:reset_password")

    return render(request, "auth/verify_otp.html")


def reset_password_view(request):
    if request.user.is_authenticated:
        return redirect("user:user_home")

    uid = request.session.get(SESSION_USER_KEY)
    if not uid or not request.session.get(SESSION_VERIFIED_KEY):
        messages.error(request, "Please verify your email code first.")
        return redirect("admin_panel:forgot_password")

    user = User.objects.filter(pk=uid).first()
    if user is None:
        request.session.pop(SESSION_USER_KEY, None)
        request.session.pop(SESSION_VERIFIED_KEY, None)
        return redirect("admin_panel:forgot_password")

    if request.method == "POST":
        p1 = request.POST.get("password") or ""
        p2 = request.POST.get("password_confirm") or ""
        if p1 != p2:
            messages.error(request, "Passwords do not match.")
            return render(request, "auth/reset_password.html")

        try:
            validate_password(p1, user=user)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
            return render(request, "auth/reset_password.html")

        user.set_password(p1)
        user.save()
        PasswordResetOTP.objects.filter(user=user).delete()
        request.session.pop(SESSION_USER_KEY, None)
        request.session.pop(SESSION_VERIFIED_KEY, None)
        messages.success(request, "Your password was updated. You can sign in now.")
        return redirect("admin_panel:login")

    return render(request, "auth/reset_password.html")
