from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods, require_POST
from .models import User


@require_http_methods(["GET", "POST"])
def register(request):
    context = {
        "errors": {}
    }

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        context["username"] = username
        context["email"] = email

        if not username:
            context["errors"]["username"] = "Username is required."

        if not email:
            context["errors"]["email"] = "Email is required."

        if not password:
            context["errors"]["password"] = "Password is required."

        if not confirm_password:
            context["errors"]["confirm_password"] = "Confirm password is required."

        if User.objects.filter(username=username).exists():
            context["errors"]["username"] = "Username already exists."

        if User.objects.filter(email=email).exists():
            context["errors"]["email"] = "Email already exists."

        # Password match
        if password != confirm_password:
            context["errors"]["confirm_password"] = "Passwords do not match."

        # Password validation
        try:
            validate_password(password)
        except ValidationError as e:
            context["errors"]["password"] = e.messages[0]

        # Return errors
        if context["errors"]:
            return render(
                request,
                "authentication/register.html",
                context
            )

        # Create user
        user = User.objects.create(
            username=username,
            email=email
        )

        user.set_password(password)
        user.save()

        return redirect("login")

    return render(
        request,
        "authentication/register.html"
    )


@require_http_methods(["GET", "POST"])
def login(request):
    context = {}

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        context["username"] = username

        if not username:
            context["error"] = "Username is required."
            return render(
                request,
                "authentication/login.html",
                context
            )

        if not password:
            context["error"] = "Password is required."
            return render(
                request,
                "authentication/login.html",
                context
            )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if not user:
            context["error"] = "Invalid credentials."
            return render(
                request,
                "authentication/login.html",
                context
            )

        login(request, user)

        return redirect("dashboard")

    return render(
        request,
        "authentication/login.html"
    )


@require_POST
def logout(request):
    logout(request)
    return redirect("login")