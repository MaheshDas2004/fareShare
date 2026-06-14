from decimal import Decimal
from collections import defaultdict

from expenses.models import Expense
from settlements.models import Settlement


class BalanceService:

    def get_group_balances(self, group):
        net = defaultdict(Decimal)

        expenses = Expense.objects.filter(
            group=group
        ).prefetch_related('splits')

        for expense in expenses:
            for split in expense.splits.all():
                if split.user == expense.paid_by:
                    continue
                net[expense.paid_by] += split.owed_amount
                net[split.user] -= split.owed_amount

        settlements = Settlement.objects.filter(group=group)

        for settlement in settlements:
            net[settlement.paid_by] += settlement.amount
            net[settlement.paid_to] -= settlement.amount

        return self._resolve_balances(net)

    def get_user_balances(self, user):
        from groups.models import Group

        owe = []
        owed = []

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

    def _resolve_balances(self, net):
        balances = []

        creditors = list(sorted(
            {u: amt for u, amt in net.items() if amt > 0}.items(),
            key=lambda x: -x[1]
        ))
        debtors = list(sorted(
            {u: amt for u, amt in net.items() if amt < 0}.items(),
            key=lambda x: x[1]
        ))

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