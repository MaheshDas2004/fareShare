from decimal import Decimal
from expenses.models import ExchangeRate, Currency


class CurrencyService:
    """
    Converts amounts to INR (base currency) using ExchangeRate table.
    Decision: always convert to INR for balance calculations.
    If no rate found for the exact date, falls back to the most recent rate before that date.
    If currency is already INR, returns amount as-is.
    """

    BASE_CURRENCY_CODE = "INR"

    def get_rate(self, from_currency_code: str, on_date) -> Decimal:
        """
        Returns the rate to convert 1 unit of from_currency to INR.
        Raises ValueError if no rate is available.
        """
        if from_currency_code == self.BASE_CURRENCY_CODE:
            return Decimal("1")

        try:
            from_currency = Currency.objects.get(code=from_currency_code)
            inr = Currency.objects.get(code=self.BASE_CURRENCY_CODE)
        except Currency.DoesNotExist:
            raise ValueError(f"Currency '{from_currency_code}' not found in database.")

        # Exact date first, then most recent before the expense date
        rate_obj = (
            ExchangeRate.objects
            .filter(
                from_currency=from_currency,
                to_currency=inr,
                effective_date__lte=on_date
            )
            .order_by("-effective_date")
            .first()
        )

        if not rate_obj:
            raise ValueError(
                f"No exchange rate found for {from_currency_code} → INR on or before {on_date}. "
                f"Please add a rate in the admin panel."
            )

        return rate_obj.rate

    def convert_to_inr(self, amount: Decimal, from_currency_code: str, on_date) -> Decimal:
        """
        Converts amount from from_currency to INR using rate on/before on_date.
        """
        rate = self.get_rate(from_currency_code, on_date)
        return round(Decimal(amount) * rate, 2)