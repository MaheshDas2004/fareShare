from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Group, GroupMembership

User = get_user_model()

@login_required
@require_GET
def group_list(request):
    memberships = GroupMembership.objects.filter(
        user=request.user,
        left_at__isnull=True,
        group__is_archived=False
    ).select_related("group")

    groups = [m.group for m in memberships]
    return render(request, "groups/group_list.html", {"groups": groups})


@login_required
@require_GET
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk, is_archived=False)

    membership = GroupMembership.objects.filter(
        group=group, user=request.user, left_at__isnull=True
    ).first()

    if not membership:
        return redirect("groups:group_list")

    active_members = GroupMembership.objects.filter(
        group=group, left_at__isnull=True
    ).select_related("user")

    past_members = GroupMembership.objects.filter(
        group=group, left_at__isnull=False
    ).select_related("user")

    return render(request, "groups/group_detail.html", {
        "group": group,
        "active_members": active_members,
        "past_members": past_members,
        "is_creator": group.created_by == request.user,
    })

@login_required
@require_http_methods(["GET", "POST"])
def create_group(request):
    context = {"errors": {}}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        default_currency = request.POST.get("default_currency", "INR").strip()

        context.update({
            "name": name,
            "description": description,
            "default_currency": default_currency,
        })

        if not name:
            context["errors"]["name"] = "Group name is required."

        if context["errors"]:
            return render(request, "groups/create_group.html", context)

        group = Group.objects.create(
            name=name,
            description=description,
            default_currency=default_currency,
            created_by=request.user
        )

        GroupMembership.objects.create(group=group, user=request.user)
        return redirect("groups:group_detail", pk=group.id)

    return render(request, "groups/create_group.html", context)

@login_required
@require_POST
def add_member(request, pk):
    group = get_object_or_404(Group, pk=pk, is_archived=False)

    if not GroupMembership.objects.filter(group=group, user=request.user, left_at__isnull=True).exists():
        return redirect("groups:group_list")

    identifier = request.POST.get("identifier", "").strip()
    if not identifier:
        messages.error(request, "Username or email is required.")
        return redirect("groups:group_detail", pk=group.id)

    target_user = User.objects.filter(
        Q(username__iexact=identifier) | Q(email__iexact=identifier)
    ).first()

    if not target_user:
        messages.error(request, "No user found with that username or email.")
        return redirect("groups:group_detail", pk=group.id)

    if target_user == request.user:
        messages.error(request, "You are already a member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    membership, created = GroupMembership.objects.get_or_create(
        group=group,
        user=target_user,
        defaults={"left_at": None}
    )

    if not created and membership.left_at is not None:
        membership.left_at = None
        membership.joined_at = timezone.now()
        membership.save(update_fields=["left_at", "joined_at"])
        messages.success(request, f"{target_user.username} re-added to the group.")
    elif created:
        messages.success(request, f"{target_user.username} added to the group.")
    else:
        messages.info(request, f"{target_user.username} is already an active member.")

    return redirect("groups:group_detail", pk=group.id)


@login_required
@require_POST
def remove_member(request, pk):
    group = get_object_or_404(Group, pk=pk, is_archived=False)

    if group.created_by != request.user:
        messages.error(request, "Only the group creator can remove members.")
        return redirect("groups:group_detail", pk=group.id)

    user_id = request.POST.get("user_id")
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot remove yourself — use Leave Group instead.")
        return redirect("groups:group_detail", pk=group.id)

    membership = GroupMembership.objects.filter(
        group=group, user=target_user, left_at__isnull=True
    ).first()

    if not membership:
        messages.error(request, f"{target_user.username} is not an active member.")
        return redirect("groups:group_detail", pk=group.id)

    membership.left_at = timezone.now()
    membership.save(update_fields=["left_at"])

    messages.success(request, f"{target_user.username} removed from the group.")
    return redirect("groups:group_detail", pk=group.id)


@login_required
@require_POST
def leave_group(request, pk):
    group = get_object_or_404(Group, pk=pk, is_archived=False)

    membership = GroupMembership.objects.filter(
        group=group, user=request.user, left_at__isnull=True
    ).first()

    if not membership:
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_list")

    membership.left_at = timezone.now()
    membership.save(update_fields=["left_at"])

    messages.success(request, "You have left the group.")
    return redirect("groups:group_list")