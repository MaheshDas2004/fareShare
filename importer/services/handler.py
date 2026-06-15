from django.contrib.auth import get_user_model
from decimal import Decimal

from expenses.models import Expense, ExpenseParticipant, Currency
from expenses.services.split_logic import SplitLogic
from settlements.models import Settlement
from groups.models import GroupMembership

User = get_user_model()


class ImportHandler:

    def __init__(self, group, imported_by):
        self.group = group
        self.imported_by = imported_by
        self.results = []

    def handle(self, rows):
        for row in rows:
            result = self._handle_row(row)
            self.results.append(result)
        return self.results

    def _handle_row(self, row):
        anomalies = row.get("anomalies", [])

        if "MISSING_PAID_BY" in anomalies:
            return self._result(row, "SKIPPED", "paid_by missing, row skipped")

        if "ZERO_AMOUNT" in anomalies:
            return self._result(row, "SKIPPED", "Zero amount, row skipped")

        if "INVALID_AMOUNT" in anomalies:
            return self._result(row, "SKIPPED", "Invalid amount, row skipped")

        if "DUPLICATE_EXACT" in anomalies:
            return self._result(row, "SKIPPED", "Exact duplicate, row skipped")

        if "MISSING_DESCRIPTION" in anomalies:
            return self._result(row, "SKIPPED", "Description missing, row skipped")

        if "SETTLEMENT_DETECTED" in anomalies:
            return self._create_settlement(row)

        if "DUPLICATE_DIFFERENT_AMOUNT" in anomalies:
            return self._result(row, "SKIPPED", "Conflicting duplicate, kept first row")

        return self._create_expense(row)

    def _create_expense(self, row):
        try:
            paid_by = self._get_user(row.get("paid_by"))
            if not paid_by:
                return self._result(row, "SKIPPED", "User not found")

            currency = self._get_currency(row.get("currency"))
            amount = abs(row.get("amount"))

            notes = []
            if "NEGATIVE_AMOUNT" in row.get("anomalies", []):
                notes.append("Negative amount detected, treated as refund")
            if "MISSING_CURRENCY" in row.get("anomalies", []):
                notes.append("Currency missing, defaulted to INR")
            if "AMBIGUOUS_DATE" in row.get("anomalies", []):
                notes.append("Ambiguous date, assumed current year")

            split_type = self._get_split_type(row)

            expense = Expense.objects.create(
                group=self.group,
                description=row.get("description"),
                amount=amount,
                currency=currency,
                paid_by=paid_by,
                split_type=split_type,
                date=row.get("date"),
                notes=", ".join(notes),
                created_by=self.imported_by
            )

            participants = self._get_participants_with_shares(row)

            if not participants:
                expense.delete()
                return self._result(row, "SKIPPED", "No valid participants found")

            for p in participants:
                print(f"DEBUG: user={p['user']}, share={p['share']}, type={type(p['share'])}")
                ExpenseParticipant.objects.create(
                    expense=expense,
                    user=p["user"],
                    is_included=True,
                    share=p["share"] if split_type != "EQUAL" else None
                )

            engine = SplitLogic()
            engine.calculate(expense)

            return self._result(row, "IMPORTED", ", ".join(notes) or "Imported successfully")

        except Exception as e:
            return self._result(row, "SKIPPED", f"Error: {str(e)}")

    def _create_settlement(self, row):
        try:
            paid_by = self._get_user(row.get("paid_by"))
            split_with = row.get("split_with")

            if not paid_by or not split_with:
                return self._result(row, "SKIPPED", "Settlement missing paid_by or paid_to")

            paid_to = self._get_user(split_with.split(";")[0].strip())
            if not paid_to:
                return self._result(row, "SKIPPED", "paid_to user not found")

            currency = self._get_currency(row.get("currency"))

            Settlement.objects.create(
                group=self.group,
                paid_by=paid_by,
                paid_to=paid_to,
                amount=abs(row.get("amount")),
                currency=currency,
                date=row.get("date"),
                notes="Settlement imported from CSV",
                created_by=self.imported_by
            )

            return self._result(row, "CONVERTED", "Settlement detected, converted to settlement record")

        except Exception as e:
            return self._result(row, "SKIPPED", f"Error: {str(e)}")

    def _get_user(self, name):
        if not name:
            return None
        return User.objects.filter(username__iexact=name).first()

    def _get_currency(self, code):
        if not code:
            code = self.group.default_currency or "INR"
        currency, _ = Currency.objects.get_or_create(
            code=code.upper(),
            defaults={"name": code, "symbol": code}
        )
        return currency

    def _get_split_type(self, row):
        split_type = (row.get("split_type") or "EQUAL").upper()
        mapping = {
            "EQUAL": "EQUAL",
            "UNEQUAL": "UNEQUAL",
            "PERCENT": "PERCENT",
            "PERCENTAGE": "PERCENT",
            "SHARES": "SHARES",
        }
        return mapping.get(split_type, "EQUAL")

    def _get_participants_with_shares(self, row):
        split_with = row.get("split_with")
        split_details = row.get("split_details")

        if not split_with:
            return []

        if ";" in split_with:
            names = [n.strip() for n in split_with.split(";")]
        else:
            names = [n.strip() for n in split_with.split(",")]

        share_map = {}
        if split_details:
            parts = split_details.replace(",", ";").split(";")
            for part in parts:
                part = part.strip()
                tokens = part.rsplit(" ", 1)
                if len(tokens) == 2:
                    name, amount = tokens
                    try:
                        amount = amount.strip().replace("%", "")  # ⬅️ % remove karo
                        share_map[name.strip().lower()] = Decimal(amount)
                    except Exception:
                        pass

        active_members = GroupMembership.objects.filter(
            group=self.group,
            left_at__isnull=True
        ).values_list("user__username", flat=True)

        participants = []
        for name in names:
            if name.lower() not in [m.lower() for m in active_members]:
                continue
            user = self._get_user(name)
            if user:
                share = share_map.get(name.lower())
                participants.append({"user": user, "share": share})

        return participants

    def _result(self, row, action, note):
        return {
            "row_number": row.get("row_number"),
            "action": action,
            "note": note,
            "anomalies": row.get("anomalies", []),
            "raw_data": row
        }