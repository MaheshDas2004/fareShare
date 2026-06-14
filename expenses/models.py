from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.symbol})"


class ExchangeRate(models.Model):
    """
    Stores conversion rates TO the base currency (INR).
    e.g. from_currency=USD, to_currency=INR, rate=83.50
    means 1 USD = 83.50 INR.

    Always convert TO INR for balance calculations.
    If from_currency == to_currency, rate = 1.
    """
    from_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="rates_from"
    )
    to_currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name="rates_to"
    )
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    effective_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One rate per currency pair per date
        unique_together = ("from_currency", "to_currency", "effective_date")
        ordering = ["-effective_date"]

    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code} on {self.effective_date}"


class Expense(models.Model):
    SPLIT_TYPES = [
        ("EQUAL", "Equal"),
        ("UNEQUAL", "Unequal"),
        ("PERCENT", "Percentage"),
        ("SHARES", "Shares"),
    ]

    group = models.ForeignKey(
        "groups.Group",
        on_delete=models.CASCADE,
        related_name="expenses"
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="expenses"
    )
    paid_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="expenses_paid"
    )
    split_type = models.CharField(max_length=20, choices=SPLIT_TYPES, default="EQUAL")
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="expenses_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.description} - {self.amount} {self.currency.code}"


class ExpenseParticipant(models.Model):
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="participants"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="expense_participations"
    )
    is_included = models.BooleanField(default=True)
    # Raw input: amount for UNEQUAL, percentage for PERCENT, ratio for SHARES
    share = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("expense", "user")
        indexes = [models.Index(fields=["expense", "user"])]

    def __str__(self):
        return f"{self.user} in expense {self.expense_id}"


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="splits"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="expense_splits"
    )
    # Final calculated amount in the expense's original currency
    owed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Cached converted amount in INR for balance calculations
    owed_amount_inr = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("expense", "user")
        indexes = [models.Index(fields=["expense", "user"])]

    def __str__(self):
        return f"{self.user} owes {self.owed_amount} {self.expense.currency.code} for expense {self.expense_id}"