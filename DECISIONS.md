# DECISIONS.md — Decision Log

## Decision 1: Core Django vs DRF
**Options considered:**
- Django REST Framework (DRF)
- Core Django with function-based views

**Decision:** Core Django with function-based views.

**Reason:** The assignment required a working app, not an API. Core Django with templates is simpler, faster to build, and easier to reason about for a 2-day project. DRF adds unnecessary complexity when there is no separate frontend.

---

## Decision 2: Soft Delete vs Hard Delete for Expenses
**Options considered:**
- Soft delete — set `is_deleted = True`, keep record in DB
- Hard delete — permanently remove from DB

**Decision:** Hard delete.

**Reason:** The assignment did not require expense history or audit trail for deleted expenses. Soft delete adds query complexity (filtering `is_deleted=False` everywhere). Hard delete is simpler and sufficient for this use case.

---

## Decision 3: Settlement as Separate App
**Options considered:**
- Put settlements inside expenses app
- Create a separate settlements app

**Decision:** Separate `settlements` app.

**Reason:** Settlements have a completely different responsibility than expenses. Expenses track spending; settlements track debt repayment. Keeping them separate follows Django's "separation of concerns" principle and makes each app easier to maintain.

---

## Decision 4: Balance Calculation in Common App
**Options considered:**
- Put BalanceService in expenses app
- Put BalanceService in settlements app
- Create a common app for shared services

**Decision:** `common` app with `BalanceService`.

**Reason:** Balance calculation requires data from both `expenses` and `settlements` apps. Putting it in either app would create a circular import. A `common` app cleanly solves this with no circular dependencies.

---

## Decision 5: Settlement Clears Balance Automatically
**Options considered:**
- Mark expenses as `is_settled = True` when settled
- Record settlements separately and recalculate balance each time

**Decision:** Record settlements separately, recalculate balance each time.

**Reason:** Recalculating from both expenses and settlements gives an always-accurate balance. Marking expenses as settled is error-prone — partial settlements are hard to track, and deleting a settlement would require manually un-settling expenses.

---

## Decision 6: CSV Import — Group Required
**Options considered:**
- Auto-create a group from CSV
- Require user to select an existing group before import

**Decision:** Require user to select an existing group.

**Reason:** CSV has no group column. Auto-creating a group would require guessing the group name. Requiring selection is explicit and gives the user full control over which group the expenses belong to.

---

## Decision 7: Duplicate Detection Policy
**Options considered:**
- Flag duplicates and ask user to decide
- Auto-skip exact duplicates, keep first for conflicting duplicates

**Decision:** Auto-skip exact duplicates, keep first row for conflicting duplicates.

**Reason:** Exact duplicates (same description + amount + date) are clearly errors — no ambiguity. Conflicting duplicates (same description + date, different amount) are harder — we keep the first row as it was logged first, and report the conflict clearly to the user.

---

## Decision 8: Inactive Members in Splits
**Options considered:**
- Include all members named in CSV regardless of membership status
- Only include currently active members

**Decision:** Only include currently active members.

**Reason:** Sam's request: "I moved in mid-April. Why would March electricity affect my balance?" — members should only be split into expenses during their active membership period. Inactive members are excluded silently and the import report notes this.

---

## Decision 9: Negative Amounts
**Options considered:**
- Skip negative amounts as errors
- Treat as refunds

**Decision:** Treat as refunds — take absolute value and note it.

**Reason:** Row 25 (Parasailing refund, -30 USD) is clearly a refund, not a data error. Skipping it would lose real financial data. Treating it as a positive expense with a note preserves the data accurately.

---

## Decision 10: Missing Currency
**Options considered:**
- Skip rows with missing currency
- Default to group's default currency (INR)

**Decision:** Default to INR and note it in import report.

**Reason:** Skipping rows for a missing currency loses valid expense data. INR is the group's default currency and the most common currency in the CSV, making it a safe default.