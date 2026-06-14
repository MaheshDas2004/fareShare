from decimal import Decimal
from collections import defaultdict
from ..models import ExpenseSplit, Expense


class BalanceService:

    # -------------------------
    # GROUP LEVEL BALANCES
    # -------------------------
    def get_group_balances(self, group):
        """
        Returns: [
            { 'from_user': userA, 'to_user': userB, 'amount': Decimal }
        ]
        """
        net = defaultdict(Decimal)  # net[user] = kitna milega/dena hai

        expenses = Expense.objects.filter(
            group=group,
            is_settled=False
        ).prefetch_related('splits')

        for expense in expenses:
            for split in expense.splits.all():
                if split.user == expense.paid_by:
                    continue  # apna hissa ignore karo

                # paid_by ko milega
                net[expense.paid_by] += split.owed_amount
                # split user ko dena hai
                net[split.user] -= split.owed_amount

        return self._resolve_balances(net)

    # -------------------------
    # INDIVIDUAL LEVEL BALANCES
    # -------------------------
    def get_user_balances(self, user):
        """
        Returns: {
            'owe': [{ 'to_user': userB, 'amount': X, 'group': group }],
            'owed': [{ 'from_user': userA, 'amount': X, 'group': group }]
        }
        """
        from groups.models import Group

        owe = []    # mujhe dena hai
        owed = []   # mujhe milega

        groups = Group.objects.filter(members=user)

        for group in groups:
            balances = self.get_group_balances(group)

            for b in balances:
                if b['from_user'] == user:
                    owe.append({
                        'to_user': b['to_user'],
                        'amount': b['amount'],
                        'group': group
                    })
                elif b['to_user'] == user:
                    owed.append({
                        'from_user': b['from_user'],
                        'amount': b['amount'],
                        'group': group
                    })

        return {'owe': owe, 'owed': owed}

    # -------------------------
    # NET BALANCE RESOLVER
    # -------------------------
    def _resolve_balances(self, net):
        """
        net dict se who owes whom nikalta hai
        """
        balances = []

        creditors = {u: amt for u, amt in net.items() if amt > 0}  # jinhe milega
        debtors = {u: amt for u, amt in net.items() if amt < 0}    # jinhe dena hai

        creditors = sorted(creditors.items(), key=lambda x: -x[1])
        debtors = sorted(debtors.items(), key=lambda x: x[1])

        creditors = list(creditors)
        debtors = list(debtors)

        i, j = 0, 0

        while i < len(creditors) and j < len(debtors):
            creditor, credit_amt = creditors[i]
            debtor, debt_amt = debtors[j]

            debt_amt = abs(debt_amt)
            settle = min(credit_amt, debt_amt)

            balances.append({
                'from_user': debtor,
                'to_user': creditor,
                'amount': round(settle, 2)
            })

            creditors[i] = (creditor, credit_amt - settle)
            debtors[j] = (debtor, -(debt_amt - settle))

            if creditors[i][1] == 0:
                i += 1
            if debtors[j][1] == 0:
                j += 1

        return balances