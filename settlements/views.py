from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.db import transaction
from .models import Settlement
from groups.models import Group
User = get_user_model()


@require_POST
@login_required
@transaction.atomic
def create_settlement(request):
    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not group.members.filter(id=request.user.id).exists():
        messages.error(request, "Tum is group ke member nahi ho")
        return redirect("group_detail", pk=group.id)

    paid_by = get_object_or_404(User, id=request.POST.get("paid_by"))
    paid_to = get_object_or_404(User, id=request.POST.get("paid_to"))

    if not group.members.filter(id=paid_by.id).exists():
        messages.error(request, "Yeh user group ka member nahi hai")
        return redirect("group_detail", pk=group.id)

    if not group.members.filter(id=paid_to.id).exists():
        messages.error(request, "Yeh user group ka member nahi hai")
        return redirect("group_detail", pk=group.id)

    if paid_by == paid_to:
        messages.error(request, "Ek hi user ko paid_by aur paid_to nahi rakha ja sakta")
        return redirect("group_detail", pk=group.id)

    try:
        amount = request.POST.get("amount")

        if not amount or float(amount) <= 0:
            messages.error(request, "Amount sahi hona chahiye")
            return redirect("group_detail", pk=group.id)

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

        messages.success(request, f"{paid_by} ne {paid_to} ko {amount} de diye!")
        return redirect("group_detail", pk=group.id)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect("group_detail", pk=group.id)


@require_POST
@login_required
def delete_settlement(request, pk):
    settlement = get_object_or_404(Settlement, id=pk)

    if not settlement.group.members.filter(id=request.user.id).exists():
        messages.error(request, "Tum is group ke member nahi ho")
        return redirect("group_detail", pk=settlement.group.id)

    group_id = settlement.group.id
    settlement.delete()
    messages.success(request, "Settlement delete ho gaya!")
    return redirect("group_detail", pk=group_id)