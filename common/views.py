from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from decimal import Decimal

from expenses.models import Expense
from groups.models import Group
from common.services.balance_service import BalanceService


@login_required
def dashboard(request):
    groups = Group.objects.filter(
        memberships__user=request.user,
        memberships__left_at__isnull=True,
        is_archived=False,
    ).distinct().order_by("-created_at")

    recent_expenses = (
        Expense.objects.filter(group__in=groups)
        .select_related("group", "paid_by", "currency")
        .order_by("-created_at")[:6]
    )

    balances = BalanceService().get_user_balances(request.user)
    total_owe = sum((item["amount"] for item in balances["owe"]), Decimal("0"))
    total_owed = sum((item["amount"] for item in balances["owed"]), Decimal("0"))

    return render(request, "common/dashboard.html", {
        "groups": groups,
        "recent_expenses": recent_expenses,
        "balances": balances,
        "total_owe": total_owe,
        "total_owed": total_owed,
    })
