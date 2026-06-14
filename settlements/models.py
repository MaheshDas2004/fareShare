from django.db import models
from django.contrib.auth import get_user_model
from expenses.models import Currency

User = get_user_model()


class Settlement(models.Model):
    group = models.ForeignKey(
        "groups.Group",
        on_delete=models.CASCADE,
        related_name="settlements"
    )

    paid_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="settlements_paid"
    )

    paid_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="settlements_received"
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2)

    currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="settlements"
    )

    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="settlements_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.paid_by} → {self.paid_to} = {self.amount}"