from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_GET
from .models import Group, GroupMembership

@login_required
@require_GET
def group_list(request):
    memberships = GroupMembership.objects.filter(user=request.user,left_at__isnull=True,group__is_archived=False).select_related("group")
    groups = [membership.group for membership in memberships]

    context = {
        "groups": groups
    }
    return render(request, "groups/group_list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def create_group(request):
    context = {
        "errors": {}
    }

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        default_currency = request.POST.get("default_currency", "INR").strip()

        context.update({
            "name": name,
            "description": description,
            "default_currency": default_currency
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

        GroupMembership.objects.create(
            group=group,
            user=request.user
        )

        return redirect("groups:group_detail", pk=group.id)

    return render(request, "groups/create_group.html")


@login_required
@require_GET
def group_detail(request, pk):
    group = get_object_or_404(
        Group,
        pk=pk,
        is_archived=False
    )

    membership = GroupMembership.objects.filter(
        group=group,
        user=request.user,
        left_at__isnull=True
    ).first()

    if not membership:
        return redirect("groups:group_list")

    active_members = GroupMembership.objects.filter(
        group=group,
        left_at__isnull=True
    ).select_related("user")

    past_members = GroupMembership.objects.filter(
        group=group,
        left_at__isnull=False
    ).select_related("user")

    context = {
        "group": group,
        "active_members": active_members,
        "past_members": past_members
    }

    return render(request, "groups/group_detail.html", context)