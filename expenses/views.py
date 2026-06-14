from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import get_user_model
from .models import Expense, ExpenseParticipant
from .services.split_logic import SplitLogic
from common.services.balance_service import BalanceService
from groups.models import Group, GroupMembership
from django.views.decorators.http import require_POST

User = get_user_model()


def is_active_member(group, user):
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        left_at__isnull=True
    ).exists()


@require_POST
@login_required
@transaction.atomic
def create_expense(request):
    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not is_active_member(group, request.user):
        messages.error(request, "Tum is group ke member nahi ho")
        return redirect("groups:group_detail", pk=group.id)

    paid_by = get_object_or_404(User, id=request.POST.get("paid_by"))

    if not is_active_member(group, paid_by):
        messages.error(request, "Yeh user group ka member nahi hai")
        return redirect("groups:group_detail", pk=group.id)

    try:
        split_type = request.POST.get("split_type")
        participants = request.POST.getlist("participants")
        shares = request.POST.getlist("shares")

        if not participants:
            messages.error(request, "Koi participant nahi chuna")
            return redirect("groups:group_detail", pk=group.id)

        if split_type != "EQUAL" and len(shares) != len(participants):
            messages.error(request, "Har participant ka share hona chahiye")
            return redirect("groups:group_detail", pk=group.id)

        expense = Expense.objects.create(
            group=group,
            description=request.POST.get("description"),
            amount=request.POST.get("amount"),
            currency_id=request.POST.get("currency_id"),
            paid_by=paid_by,
            split_type=split_type,
            date=request.POST.get("date"),
            notes=request.POST.get("notes", ""),
            created_by=request.user
        )

        for index, user_id in enumerate(participants):
            user = get_object_or_404(User, id=user_id)
            ExpenseParticipant.objects.create(
                expense=expense,
                user=user,
                is_included=True,
                share=shares[index] if split_type != "EQUAL" else None
            )

        engine = SplitLogic()
        engine.calculate(expense)

        messages.success(request, "Expense successfully create ho gaya!")
        return redirect("groups:group_detail", pk=group.id)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect("groups:group_detail", pk=group.id)


@require_POST
@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, id=pk)

    if expense.created_by != request.user:
        messages.error(request, "Tum yeh expense delete nahi kar sakte")
        return redirect("groups:group_detail", pk=expense.group.id)

    group_id = expense.group.id
    expense.delete()
    messages.success(request, "Expense delete ho gaya!")
    return redirect("groups:group_detail", pk=group_id)


@login_required
def group_balances(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_active_member(group, request.user):
        messages.error(request, "Tum is group ke member nahi ho")
        return redirect("groups:group_detail", pk=group_id)

    service = BalanceService()
    balances = service.get_group_balances(group)

    return render(request, "expenses/group_balances.html", {
        "group": group,
        "balances": balances
    })


@login_required
def user_balances(request):
    service = BalanceService()
    balances = service.get_user_balances(request.user)

    return render(request, "expenses/user_balances.html", {
        "balances": balances
    })