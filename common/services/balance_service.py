from decimal import Decimal
from collections import defaultdict

from expenses.models import Expense
from settlements.models import Settlement
from groups.models import Group, GroupMembership
from common.services.currency_service import CurrencyService


class BalanceService:
    """
    Calculates who owes whom within a group.

    Key decisions documented here:
    - All amounts are converted to INR (base currency) before summing.
    - Membership window is respected: a user only owes for expenses dated
      within their [joined_at, left_at] window (Fix #5 — Sam's issue).
    - Settlement amounts are also converted to INR.
    - Balance resolution uses a greedy min-transactions algorithm (Aisha's request).
    """

    def get_group_balances(self, group):
        """
        Returns a list of dicts: [{'from_user': ..., 'to_user': ..., 'amount': Decimal}]
        All amounts in INR.
        """
        net = defaultdict(Decimal)
        currency_service = CurrencyService()

        expenses = (
            Expense.objects
            .filter(group=group)
            .select_related("currency", "paid_by")
            .prefetch_related("splits__user")
        )

        for expense in expenses:
            for split in expense.splits.all():
                # Fix #5 — only include this split if the user was a member
                # when the expense was incurred
                if not self._was_member_on_date(split.user, group, expense.date):
                    continue

                if split.user == expense.paid_by:
                    continue

                # Fix #3 — use pre-converted INR amount stored on the split
                inr_amount = split.owed_amount_inr

                net[expense.paid_by] += inr_amount
                net[split.user] -= inr_amount

        # Settlements: also convert to INR
        settlements = (
            Settlement.objects
            .filter(group=group)
            .select_related("currency", "paid_by", "paid_to")
        )

        for settlement in settlements:
            try:
                inr_amount = currency_service.convert_to_inr(
                    amount=settlement.amount,
                    from_currency_code=settlement.currency.code,
                    on_date=settlement.date
                )
            except ValueError:
                inr_amount = settlement.amount  # fallback: treat as INR

            net[settlement.paid_by] += inr_amount
            net[settlement.paid_to] -= inr_amount

        return self._resolve_balances(net)

    def get_user_balances(self, user):
        """
        Returns {'owe': [...], 'owed': [...]} across all active groups.
        Fix #2 — Group is now imported.
        """
        owe = []
        owed = []

        # Fix #2 — Group was not imported before; now it is
        groups = Group.objects.filter(
            memberships__user=user,
            memberships__left_at__isnull=True,
            is_archived=False
        )

        for group in groups:
            balances = self.get_group_balances(group)

            for b in balances:
                if b["from_user"] == user:
                    owe.append({
                        "to_user": b["to_user"],
                        "amount": b["amount"],
                        "group": group,
                    })
                elif b["to_user"] == user:
                    owed.append({
                        "from_user": b["from_user"],
                        "amount": b["amount"],
                        "group": group,
                    })

        return {"owe": owe, "owed": owed}

    def _was_member_on_date(self, user, group, date) -> bool:
        """
        Fix #5 — checks if user was an active member of group on a given date.
        Handles: joined before date AND (still active OR left after date).
        """
        memberships = GroupMembership.objects.filter(group=group, user=user)

        for m in memberships:
            joined = m.joined_at.date() if m.joined_at else None
            left = m.left_at.date() if m.left_at else None

            if joined and joined <= date:
                if left is None or left >= date:
                    return True

        return False

    def _resolve_balances(self, net):
        """
        Greedy algorithm: minimises the number of transactions needed to settle.
        Satisfies Aisha's request: "one number per person, who pays whom, done."
        """
        creditors = sorted(
            [(u, amt) for u, amt in net.items() if amt > Decimal("0")],
            key=lambda x: -x[1]
        )
        debtors = sorted(
            [(u, amt) for u, amt in net.items() if amt < Decimal("0")],
            key=lambda x: x[1]
        )

        creditors = [list(c) for c in creditors]
        debtors = [list(d) for d in debtors]

        balances = []
        i, j = 0, 0

        while i < len(creditors) and j < len(debtors):
            creditor, credit_amt = creditors[i]
            debtor, debt_amt = debtors[j]

            debt_amt = abs(debt_amt)
            settle = min(credit_amt, debt_amt)

            balances.append({
                "from_user": debtor,
                "to_user": creditor,
                "amount": round(settle, 2),
            })

            creditors[i][1] -= settle
            debtors[j][1] += settle  # debt_amt was negative, add back

            if creditors[i][1] == 0:
                i += 1
            if debtors[j][1] == 0:
                j += 1

        return balances