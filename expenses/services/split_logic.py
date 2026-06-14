from decimal import Decimal
from ..models import ExpenseSplit
from common.services.currency_service import CurrencyService


class SplitLogic:
    """
    Calculates how an expense is split among participants.
    Saves ExpenseSplit rows with both the original-currency amount
    and the INR-equivalent (for balance calculations).
    """

    def calculate(self, expense):
        participants = expense.participants.filter(is_included=True)

        if not participants.exists():
            raise ValueError("No participants found for this expense.")

        dispatch = {
            "EQUAL": self.equal_split,
            "UNEQUAL": self.unequal_split,
            "PERCENT": self.percent_split,
            "SHARES": self.shares_split,
        }

        handler = dispatch.get(expense.split_type)
        if not handler:
            raise ValueError(f"Unknown split type: {expense.split_type}")

        splits = handler(expense, participants)
        self.save_splits(expense, splits)
        return splits

    def equal_split(self, expense, participants):
        count = participants.count()
        per_person = round(Decimal(expense.amount) / Decimal(count), 2)

        splits = [{"user": p.user, "amount": per_person} for p in participants]

        total_split = per_person * count
        remainder = Decimal(expense.amount) - total_split
        if remainder:
            splits[-1]["amount"] += remainder

        return splits

    def unequal_split(self, expense, participants):
        total = Decimal("0")
        splits = []

        for p in participants:
            if p.share is None:
                raise ValueError(f"Share amount missing for {p.user} in UNEQUAL split.")
            total += Decimal(p.share)
            splits.append({"user": p.user, "amount": Decimal(p.share)})

        if round(total, 2) != round(Decimal(expense.amount), 2):
            raise ValueError(
                f"Unequal shares sum to {total}, but expense total is {expense.amount}."
            )

        return splits

    def percent_split(self, expense, participants):
        total_percent = Decimal("0")
        splits = []

        for p in participants:
            if p.share is None:
                raise ValueError(f"Percentage missing for {p.user} in PERCENT split.")
            total_percent += Decimal(p.share)
            amount = round((Decimal(expense.amount) * Decimal(p.share)) / 100, 2)
            splits.append({"user": p.user, "amount": amount})

        if round(total_percent, 2) != Decimal("100"):
            raise ValueError(
                f"Percentages sum to {total_percent}%, must sum to 100%."
            )

        calculated_total = sum(s["amount"] for s in splits)
        remainder = Decimal(expense.amount) - calculated_total
        if remainder:
            splits[-1]["amount"] += remainder

        return splits

    def shares_split(self, expense, participants):
        participants = list(participants)

        for p in participants:
            if p.share is None:
                raise ValueError(f"Share ratio missing for {p.user} in SHARES split.")

        total_shares = sum(Decimal(p.share) for p in participants)

        if total_shares == 0:
            raise ValueError("Total shares cannot be 0.")

        splits = []
        for p in participants:
            amount = round(
                (Decimal(expense.amount) * Decimal(p.share)) / total_shares, 2
            )
            splits.append({"user": p.user, "amount": amount})

        # Fix remainder from rounding
        calculated_total = sum(s["amount"] for s in splits)
        remainder = Decimal(expense.amount) - calculated_total
        if remainder:
            splits[-1]["amount"] += remainder

        return splits

    def save_splits(self, expense, splits):
        currency_service = CurrencyService()

        for item in splits:
            try:
                owed_inr = currency_service.convert_to_inr(
                    amount=item["amount"],
                    from_currency_code=expense.currency.code,
                    on_date=expense.date
                )
            except ValueError:
                # If no rate found, store 0 and surface this to the user
                # The importer will catch this; manual entry should require a rate
                owed_inr = Decimal("0")

            ExpenseSplit.objects.update_or_create(
                expense=expense,
                user=item["user"],
                defaults={
                    "owed_amount": item["amount"],
                    "owed_amount_inr": owed_inr,
                }
            )