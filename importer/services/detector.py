class AnomalyDetector:

    def detect(self, rows):
        results = []
        seen = {}

        for row in rows:
            anomalies = list(row.get("anomalies", []))

            if not row.get("paid_by"):
                anomalies.append("MISSING_PAID_BY")

            if not row.get("description"):
                anomalies.append("MISSING_DESCRIPTION")

            description = (row.get("description") or "").lower()
            settlement_keywords = ["paid back", "settled", "repaid", "returned", "settlement"]
            if any(keyword in description for keyword in settlement_keywords):
                anomalies.append("SETTLEMENT_DETECTED")

            key = (
                row.get("description", "").lower().strip(),
                str(row.get("amount")),
                str(row.get("date"))
            )

            fuzzy_key = (
                row.get("description", "").lower().strip(),
                str(row.get("date"))
            )

            if key in seen:
                anomalies.append("DUPLICATE_EXACT")
            elif fuzzy_key in seen:
                anomalies.append("DUPLICATE_DIFFERENT_AMOUNT")
            else:
                seen[key] = row
                seen[fuzzy_key] = row

            row["anomalies"] = anomalies
            results.append(row)

        return results