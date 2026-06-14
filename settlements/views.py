from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.db import transaction

from .models import Settlement
from groups.models import Group, GroupMembership

User = get_user_model()

def is_active_member(group, user):
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        left_at__isnull=True
    ).exists()


def can_manage_settlement(settlement, user):
    return (
        settlement.created_by == user
        or settlement.group.created_by == user
    )

@require_POST
@login_required
@transaction.atomic
def create_settlement(request):
    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not is_active_member(group, request.user):
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    paid_by = get_object_or_404(User, id=request.POST.get("paid_by"))
    paid_to = get_object_or_404(User, id=request.POST.get("paid_to"))

    if not is_active_member(group, paid_by):
        messages.error(request, f"{paid_by.username} is not an active member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    if not is_active_member(group, paid_to):
        messages.error(request, f"{paid_to.username} is not an active member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    if paid_by == paid_to:
        messages.error(request, "Payer and payee cannot be the same person.")
        return redirect("groups:group_detail", pk=group.id)

    try:
        amount = request.POST.get("amount", "").strip()

        if not amount:
            messages.error(request, "Amount is required.")
            return redirect("groups:group_detail", pk=group.id)

        amount_decimal = float(amount)
        if amount_decimal <= 0:
            messages.error(request, "Amount must be greater than zero.")
            return redirect("groups:group_detail", pk=group.id)

        Settlement.objects.create(
            group=group,
            paid_by=paid_by,
            paid_to=paid_to,
            amount=amount,
            currency_id=request.POST.get("currency_id"),
            date=request.POST.get("date"),
            notes=request.POST.get("notes", ""),
            created_by=request.user
        )

        messages.success(
            request,
            f"{paid_by.username} paid {paid_to.username} ₹{amount}. Balance updated."
        )
        return redirect("groups:group_detail", pk=group.id)

    except (ValueError, TypeError) as e:
        messages.error(request, f"Invalid data: {e}")
        return redirect("groups:group_detail", pk=group.id)


@require_POST
@login_required
def delete_settlement(request, pk):
    settlement = get_object_or_404(Settlement, id=pk)

    if not can_manage_settlement(settlement, request.user):
        messages.error(request, "You do not have permission to delete this settlement.")
        return redirect("groups:group_detail", pk=settlement.group.id)

    group_id = settlement.group.id
    settlement.delete()
    messages.success(request, "Settlement deleted.")
    return redirect("groups:group_detail", pk=group_id)