# SCOPE.md — Anomaly Log & Database Schema

## Data Anomalies Found in expenses_export.csv

### Anomaly 1: Missing paid_by (Row 12)
**Problem:** `paid_by` field is empty/null.
**Policy:** Skip the row. An expense cannot exist without knowing who paid.
**Action:** Row skipped, reported in import report.

---

### Anomaly 2: Zero Amount (Row 30)
**Problem:** Expense amount is ₹0.
**Policy:** Skip the row. A zero amount expense has no financial meaning.
**Action:** Row skipped, reported in import report.

---

### Anomaly 3: Invalid Amount (Row 6)
**Problem:** Amount field is empty or non-numeric.
**Policy:** Skip the row. Cannot create an expense without a valid amount.
**Action:** Row skipped, reported in import report.

---

### Anomaly 4: Exact Duplicate (Rows 4 & 5)
**Problem:** Two rows with same description, amount, and date.
**Policy:** Keep the first row, skip the second.
**Action:** First row imported, duplicate skipped, reported in import report.

---

### Anomaly 5: Duplicate with Different Amount (Rows 23 & 24)
**Problem:** Same description and date but different amounts — two people logged the same dinner differently.
**Policy:** Keep the first row, skip the second. First logger wins.
**Action:** First row imported, conflicting duplicate skipped, reported in import report.

---

### Anomaly 6: Settlement Recorded as Expense (Row 13)
**Problem:** Row describes a payment between users ("Rohan paid Aisha back") — this is a settlement, not an expense.
**Detection:** Description contains keywords: "paid back", "settled", "repaid", "returned", "settlement".
**Policy:** Convert to a Settlement record instead of an Expense.
**Action:** Row converted to Settlement, reported in import report.

---

### Anomaly 7: Negative Amount (Row 25)
**Problem:** Amount is negative (-30 USD) — likely a refund.
**Policy:** Treat as a refund expense. Take absolute value of amount and note it in expense notes.
**Action:** Imported as expense with note "Negative amount detected, treated as refund".

---

### Anomaly 8: Missing Currency (Row 27)
**Problem:** Currency field is empty/null.
**Policy:** Default to group's default currency (INR).
**Action:** Imported with INR currency, noted in expense notes.

---

### Anomaly 9: Inconsistent Date Formats
**Problem:** Dates appear in multiple formats — `20-02-2026`, `Feb-14`, `2026-02-20`.
**Policy:** Try multiple known formats in order. If year is missing, assume current year.
**Action:** Date parsed with best guess, ambiguous dates noted in import report.

---

### Anomaly 10: Ambiguous Date (Row 32)
**Problem:** Date like `04-05-2026` could be April 5 or May 4.
**Policy:** Always treat as DD-MM-YYYY format.
**Action:** Imported as 4th May 2026, noted in import report.

---

### Anomaly 11: Inactive Member in Split (Meera after March)
**Problem:** Meera left the flat end of March but appears in splits for April expenses.
**Policy:** Only include currently active group members in splits. Inactive members are silently excluded.
**Action:** Meera excluded from April splits, expense imported with remaining active members.

---

### Anomaly 12: Percentages Not Summing to 100 (Row 14)
**Problem:** `Aisha 30%; Rohan 30%; Priya 30%; Meera 20%` sums to 110%.
**Policy:** Import as-is and let SplitLogic raise a validation error — row is skipped with error note.
**Action:** Row skipped, error reported in import report.

---

## Database Schema

### authentication app
**User** (Django default)
- id, username, email, password

---

### groups app
**Group**
- id
- name `CharField`
- description `TextField`
- created_by `ForeignKey(User)`
- default_currency `CharField` (default: INR)
- is_archived `BooleanField`
- created_at, updated_at `DateTimeField`

**GroupMembership**
- id
- group `ForeignKey(Group)`
- user `ForeignKey(User)`
- joined_at `DateTimeField`
- left_at `DateTimeField` (null = still active)

---

### expenses app
**Currency**
- id
- code `CharField` (e.g. INR, USD)
- name `CharField`
- symbol `CharField`
- is_active `BooleanField`

**Expense**
- id
- group `ForeignKey(Group)`
- description `CharField`
- amount `DecimalField`
- currency `ForeignKey(Currency)`
- paid_by `ForeignKey(User)`
- split_type `CharField` (EQUAL/UNEQUAL/PERCENT/SHARES)
- date `DateField`
- notes `TextField`
- created_by `ForeignKey(User)`
- created_at, updated_at `DateTimeField`

**ExpenseParticipant**
- id
- expense `ForeignKey(Expense)`
- user `ForeignKey(User)`
- is_included `BooleanField`
- share `DecimalField` (null for EQUAL split)

**ExpenseSplit**
- id
- expense `ForeignKey(Expense)`
- user `ForeignKey(User)`
- owed_amount `DecimalField`
- created_at `DateTimeField`

---

### settlements app
**Settlement**
- id
- group `ForeignKey(Group)`
- paid_by `ForeignKey(User)`
- paid_to `ForeignKey(User)`
- amount `DecimalField`
- currency `ForeignKey(Currency)`
- date `DateField`
- notes `TextField`
- created_by `ForeignKey(User)`
- created_at, updated_at `DateTimeField`

---

### importer app
**ImportReport**
- id
- uploaded_by `ForeignKey(User)`
- file_name `CharField`
- total_rows `IntegerField`
- imported_rows `IntegerField`
- skipped_rows `IntegerField`
- status `CharField` (PENDING/COMPLETED/FAILED)
- created_at `DateTimeField`

**ImportReportRow**
- id
- report `ForeignKey(ImportReport)`
- row_number `IntegerField`
- raw_data `JSONField`
- action `CharField` (IMPORTED/SKIPPED/CONVERTED/FLAGGED)
- anomalies `JSONField`
- note `TextField`