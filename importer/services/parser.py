import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


KNOWN_DATE_FORMATS = [
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%b-%d",
    "%d %b %Y",
    "%B %d, %Y",
]


class CSVParser:

    def parse(self, file):
        rows = []
        decoded = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))

        for index, row in enumerate(reader, start=1):
            parsed = self._parse_row(index, row)
            rows.append(parsed)

        return rows

    def _parse_row(self, index, row):
        anomalies = []

        description = self._clean_str(row.get("description"))
        paid_by = self._clean_str(row.get("paid_by"))
        amount = self._parse_amount(row.get("amount"), anomalies)
        currency = self._parse_currency(row.get("currency"), anomalies)
        date = self._parse_date(row.get("date"), anomalies)
        split_type = self._clean_str(row.get("split_type"))
        split_with = self._clean_str(row.get("split_with"))
        split_details = self._clean_str(row.get("split_details"))  # ⬅️ add karo
        notes = self._clean_str(row.get("notes"))

        return {
            "row_number": index,
            "description": description,
            "paid_by": paid_by,
            "amount": amount,
            "currency": currency,
            "date": date,
            "split_type": split_type,
            "split_with": split_with,
            "split_details": split_details,  # ⬅️ add karo
            "notes": notes,
            "anomalies": anomalies,
        }

    def _clean_str(self, value):
        if not value or str(value).strip().lower() in ("nan", "none", "null", ""):
            return None
        return str(value).strip()

    def _parse_amount(self, value, anomalies):
        try:
            # Remove thousand separator commas
            cleaned = str(value).strip().replace(",", "")
            amount = Decimal(cleaned)
            if amount < 0:
                anomalies.append("NEGATIVE_AMOUNT")
            if amount == 0:
                anomalies.append("ZERO_AMOUNT")
            return amount
        except (InvalidOperation, TypeError):
            anomalies.append("INVALID_AMOUNT")
            return None
        
    def _parse_currency(self, value, anomalies):
        cleaned = self._clean_str(value)
        if not cleaned:
            anomalies.append("MISSING_CURRENCY")
            return None
        return cleaned.upper()

    def _parse_date(self, value, anomalies):
        cleaned = self._clean_str(value)
        if not cleaned:
            anomalies.append("MISSING_DATE")
            return None

        for fmt in KNOWN_DATE_FORMATS:
            try:
                parsed = datetime.strptime(cleaned, fmt)
                if parsed.year == 1900:
                    parsed = parsed.replace(year=datetime.now().year)
                    anomalies.append("AMBIGUOUS_DATE")
                return parsed.date()
            except ValueError:
                continue

        anomalies.append("INVALID_DATE_FORMAT")
        return None