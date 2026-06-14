from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST, require_http_methods
from decimal import Decimal

from .models import Expense, ExpenseParticipant, Currency
from .services.split_logic import SplitLogic
from common.services.balance_service import BalanceService
from common.services.currency_service import CurrencyService
from groups.models import Group, GroupMembership

User = get_user_model()


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def is_active_member(group, user):
    return GroupMembership.objects.filter(
        group=group,
        user=user,
        left_at__isnull=True
    ).exists()


def can_manage_expense(expense, user):
    """
    Fix #13 — group creator OR expense creator can manage (edit/delete).
    """
    return (
        expense.created_by == user
        or expense.group.created_by == user
    )


# ------------------------------------------------------------------ #
# Expense CRUD                                                         #
# ------------------------------------------------------------------ #

@require_POST
@login_required
@transaction.atomic
def create_expense(request):
    group = get_object_or_404(Group, id=request.POST.get("group_id"))

    if not is_active_member(group, request.user):
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    paid_by_id = request.POST.get("paid_by")
    paid_by = get_object_or_404(User, id=paid_by_id)

    if not is_active_member(group, paid_by):
        messages.error(request, "The payer is not an active member of this group.")
        return redirect("groups:group_detail", pk=group.id)

    try:
        split_type = request.POST.get("split_type")
        participants = request.POST.getlist("participants")
        shares = request.POST.getlist("shares")

        if not participants:
            messages.error(request, "At least one participant is required.")
            return redirect("groups:group_detail", pk=group.id)

        if split_type != "EQUAL" and len(shares) != len(participants):
            messages.error(request, "Each participant must have a share value.")
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
            participant_user = get_object_or_404(User, id=user_id)
            ExpenseParticipant.objects.create(
                expense=expense,
                user=participant_user,
                is_included=True,
                share=shares[index] if split_type != "EQUAL" else None
            )

        engine = SplitLogic()
        engine.calculate(expense)

        messages.success(request, "Expense created successfully.")
        return redirect("groups:group_detail", pk=group.id)

    except ValueError as e:
        messages.error(request, str(e))
        return redirect("groups:group_detail", pk=group.id)


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, id=pk)

    if not can_manage_expense(expense, request.user):
        messages.error(request, "You do not have permission to edit this expense.")
        return redirect("groups:group_detail", pk=expense.group.id)

    group = expense.group
    currencies = Currency.objects.filter(is_active=True)
    currency_service = CurrencyService()
    currency_rates = {}
    for currency in currencies:
        if currency.code == "INR":
            currency_rates[currency.code] = "1"
            continue
        try:
            currency_rates[currency.code] = str(currency_service.get_rate(currency.code, expense.date))
        except ValueError:
            continue
    active_members = GroupMembership.objects.filter(
        group=group, left_at__isnull=True
    ).select_related("user")
    participant_rows = []
    participant_map = {
        participant.user_id: participant.share
        for participant in expense.participants.select_related("user").all()
    }
    selected_participants = set(expense.participants.filter(is_included=True).values_list("user_id", flat=True))

    for membership in active_members:
        participant_rows.append({
            "member": membership,
            "selected": membership.user_id in selected_participants,
            "share": participant_map.get(membership.user_id),
        })

    if request.method == "POST":
        try:
            split_type = request.POST.get("split_type")
            participants = request.POST.getlist("participants")
            shares = request.POST.getlist("shares")

            if not participants:
                messages.error(request, "At least one participant is required.")
                return redirect("expenses:edit_expense", pk=pk)

            if split_type != "EQUAL" and len(shares) != len(participants):
                messages.error(request, "Each participant must have a share value.")
                return redirect("expenses:edit_expense", pk=pk)

            expense.description = request.POST.get("description")
            expense.amount = request.POST.get("amount")
            expense.currency_id = request.POST.get("currency_id")
            expense.paid_by = get_object_or_404(User, id=request.POST.get("paid_by"))
            expense.split_type = split_type
            expense.date = request.POST.get("date")
            expense.notes = request.POST.get("notes", "")
            expense.save()

            expense.participants.all().delete()
            expense.splits.all().delete()

            for index, user_id in enumerate(participants):
                participant_user = get_object_or_404(User, id=user_id)
                ExpenseParticipant.objects.create(
                    expense=expense,
                    user=participant_user,
                    is_included=True,
                    share=shares[index] if split_type != "EQUAL" else None
                )

            engine = SplitLogic()
            engine.calculate(expense)

            messages.success(request, "Expense updated successfully.")
            return redirect("groups:group_detail", pk=group.id)

        except ValueError as e:
            messages.error(request, str(e))

    context = {
        "expense": expense,
        "group": group,
        "currencies": currencies,
        "active_members": active_members,
        "split_types": Expense.SPLIT_TYPES,
        "current_participants": expense.participants.filter(is_included=True).values_list("user_id", flat=True),
        "participant_rows": participant_rows,
        "currency_rates": currency_rates,
    }
    return render(request, "expenses/edit_expense.html", context)


@require_POST
@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, id=pk)

    if not can_manage_expense(expense, request.user):
        messages.error(request, "You do not have permission to delete this expense.")
        return redirect("groups:group_detail", pk=expense.group.id)

    group_id = expense.group.id
    expense.delete()
    messages.success(request, "Expense deleted.")
    return redirect("groups:group_detail", pk=group_id)



@login_required
def expense_list(request, group_id):
    """
    Fix #7 — lists all expenses in a group with participant breakdown.
    Satisfies Rohan: "I want to see exactly which expenses make that up."
    """
    group = get_object_or_404(Group, id=group_id)

    if not is_active_member(group, request.user):
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_list")

    expenses = (
        Expense.objects
        .filter(group=group)
        .select_related("paid_by", "currency")
        .prefetch_related("splits__user", "participants__user")
        .order_by("-date", "-created_at")
    )

    return render(request, "expenses/expense_list.html", {
        "group": group,
        "expenses": expenses,
    })


@login_required
def expense_detail(request, pk):
    expense = get_object_or_404(Expense, id=pk)
    group = expense.group

    if not is_active_member(group, request.user):
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_list")

    splits = expense.splits.select_related("user").all()
    currency_service = CurrencyService()
    try:
        expense_inr_total = currency_service.convert_to_inr(
            amount=expense.amount,
            from_currency_code=expense.currency.code,
            on_date=expense.date,
        )
    except ValueError:
        expense_inr_total = None

    split_rows = []
    for split in splits:
        split_rows.append({
            "user": split.user,
            "owed_amount": split.owed_amount,
            "owed_amount_inr": split.owed_amount_inr,
        })

    return render(request, "expenses/expense_detail.html", {
        "expense": expense,
        "group": group,
        "splits": split_rows,
        "expense_inr_total": expense_inr_total,
    })


@login_required
def group_balances(request, group_id):
    group = get_object_or_404(Group, id=group_id)

    if not is_active_member(group, request.user):
        messages.error(request, "You are not an active member of this group.")
        return redirect("groups:group_detail", pk=group_id)

    service = BalanceService()
    balances = service.get_group_balances(group)

    return render(request, "expenses/group_balances.html", {
        "group": group,
        "balances": balances,
    })


@login_required
def user_balances(request):
    service = BalanceService()
    balances = service.get_user_balances(request.user)
    balances["owe_total"] = sum((item["amount"] for item in balances["owe"]), Decimal("0"))
    balances["owed_total"] = sum((item["amount"] for item in balances["owed"]), Decimal("0"))

    return render(request, "expenses/user_balances.html", {
        "balances": balances,
    })