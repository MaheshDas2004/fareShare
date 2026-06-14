from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods, require_POST
from .models import User


@require_http_methods(["GET", "POST"])
def registerView(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    context = {"errors": {}}

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

        if username and User.objects.filter(username=username).exists():
            context["errors"]["username"] = "Username already exists."
        if email and User.objects.filter(email=email).exists():
            context["errors"]["email"] = "Email already exists."

        if password and confirm_password and password != confirm_password:
            context["errors"]["confirm_password"] = "Passwords do not match."

        if password and "password" not in context["errors"]:
            try:
                validate_password(password)
            except ValidationError as e:
                context["errors"]["password"] = e.messages[0]

        if context["errors"]:
            return render(request, "authentication/register.html", context)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        login(request, user)
        return redirect("dashboard")

    return render(request, "authentication/register.html", context)


@require_http_methods(["GET", "POST"])
def loginView(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    context = {"errors": {}}

    if request.method == "POST":
        identifier = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        context["identifier"] = identifier

        if not identifier:
            context["errors"]["login"] = "Username or Email is required."
        if not password:
            context["errors"]["login"] = "Password is required."

        if context["errors"]:
            return render(request, "authentication/login.html", context)

        user_obj = (
            User.objects.filter(username=identifier).first()
            or User.objects.filter(email=identifier).first()
        )

        if not user_obj:
            context["errors"]["login"] = "Invalid credentials."
            return render(request, "authentication/login.html", context)

        user = authenticate(request, username=user_obj.username, password=password)

        if not user:
            context["errors"]["login"] = "Invalid credentials."
            return render(request, "authentication/login.html", context)

        if not user.is_active:
            context["errors"]["login"] = "Account is disabled."
            return render(request, "authentication/login.html", context)

        login(request, user)
        return redirect("dashboard")

    return render(request, "authentication/login.html", context)


@require_POST
def logoutView(request):
    logout(request)
    return redirect("login")