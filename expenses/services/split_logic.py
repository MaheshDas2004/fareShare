from decimal import Decimal
from ..models import ExpenseSplit


class SplitLogic:

    def calculate(self, expense):
        participants = expense.participants.filter(is_included=True)

        if not participants.exists():
            raise ValueError("No participants found")

        if expense.split_type == "EQUAL":
            splits = self.equal_split(expense, participants)

        elif expense.split_type == "UNEQUAL":
            splits = self.unequal_split(expense, participants)

        elif expense.split_type == "PERCENT":
            splits = self.percent_split(expense, participants)

        elif expense.split_type == "SHARES":
            splits = self.shares_split(expense, participants)

        else:
            raise ValueError("Invalid split type")

        self.save_splits(expense, splits)
        return splits


    def equal_split(self, expense, participants):
        count = participants.count()
        amount = round(Decimal(expense.amount) / Decimal(count), 2)
        
        splits = [
            {"user": p.user, "amount": amount}
            for p in participants
        ]

        total_split = amount * count
        remainder = Decimal(expense.amount) - total_split
        splits[-1]["amount"] += remainder
        return splits
    

    def unequal_split(self, expense, participants):
        total = Decimal("0")
        splits = []

        for p in participants:
            if p.share is None:
                raise ValueError("Share missing for UNEQUAL split")

            total += Decimal(p.share)
            splits.append({"user": p.user, "amount": Decimal(p.share)})

        if round(total, 2) != round(expense.amount, 2):
            raise ValueError("Shares do not match total expense")

        return splits

    
    def percent_split(self, expense, participants):
        total_percent = Decimal("0")
        splits = []

        for p in participants:
            if p.share is None:
                raise ValueError("Percentage missing")

            total_percent += Decimal(p.share)

            amount = (Decimal(expense.amount) * Decimal(p.share)) / 100

            splits.append({"user": p.user, "amount": round(amount, 2)})

        if round(total_percent, 2) != 100:
            raise ValueError("Percentages must sum to 100")

        return splits


    def shares_split(self, expense, participants):
        splits = []

        for p in participants:
            if p.share is None:
                raise ValueError(f"{p.user} ka share missing hai SHARES split mein")
        total_shares = sum([Decimal(p.share) for p in participants])

        if total_shares == 0:
            raise ValueError("Total shares 0 nahi ho sakta")

        for p in participants:
            amount = (Decimal(expense.amount) * Decimal(p.share)) / Decimal(total_shares)
            splits.append({"user": p.user, "amount": round(amount, 2)})

        return splits
    def save_splits(self, expense, splits):
        for item in splits:
            ExpenseSplit.objects.update_or_create(
                expense=expense,
                user=item["user"],
                defaults={
                    "owed_amount": item["amount"]
                }
            )