# AI Usage Log

## AI Tool Used
Claude (claude.ai) — used as primary development collaborator

## Key Prompts
- "Review my expenses app and suggest next features"
- "Build balance calculation service"
- "Build CSV import feature with anomaly detection"
- "Fix group membership checks across all views"

---

## Cases Where AI Produced Something Wrong

### Case 1: JsonResponse in Views
**What AI did:** AI initially suggested using `JsonResponse` for all view responses, which is a DRF pattern.
**What was wrong:** The project uses core Django with HTML forms and templates — `JsonResponse` is not appropriate here.
**How I caught it:** I told Claude "I'm not using DRF, I'm using core Django."
**What I changed:** Replaced all `JsonResponse` with `redirect` and `render`, and used `messages` framework for user feedback.

---

### Case 2: group.members Filter That Didn't Exist
**What AI did:** AI wrote `group.members.filter(id=request.user.id).exists()` in views and `Group.objects.filter(members=user)` in balance service.
**What was wrong:** The `Group` model has no `members` field — membership is tracked via `GroupMembership` model with `left_at` for soft leave.
**How I caught it:** I uploaded the groups app code and AI identified the issue itself after reviewing the model.
**What I changed:** Replaced all `group.members` calls with proper `GroupMembership` queries:
```python
GroupMembership.objects.filter(
    group=group,
    user=user,
    left_at__isnull=True
).exists()
```

---

### Case 3: Circular Import in split_logic.py
**What AI did:** AI suggested `from .models import` inside `expenses/services/split_logic.py` which caused a circular import error.
**What was wrong:** `split_logic.py` is inside `expenses/services/` so the correct import is `from ..models import` (two dots, not one).
**How I caught it:** Server threw `ModuleNotFoundError: No module named 'expenses.services.models'` on startup.
**What I changed:** Fixed import to `from ..models import Expense, ExpenseParticipant`.

---

### Case 4: split_details Missing from Parser
**What AI did:** AI wrote the CSV parser but forgot to include `split_details` column in `_parse_row` return dict.
**What was wrong:** `split_details` was being read from CSV but never passed to the handler, so all shares were `None` for UNEQUAL/PERCENT splits.
**How I caught it:** Added debug prints and saw `share=None` for all participants even when CSV had correct values.
**What I changed:** Added `split_details = self._clean_str(row.get("split_details"))` to parser and included it in the return dict.

---

### Case 5: Percentage Sign in split_details
**What AI did:** AI's share parser assumed numeric values only in `split_details`.
**What was wrong:** CSV had values like `"Aisha 30%; Rohan 30%"` — the `%` sign caused `Decimal()` to fail silently.
**How I caught it:** Pizza Friday row kept failing with "Percentage missing" error even though CSV had correct data.
**What I changed:** Added `.replace("%", "")` before `Decimal()` conversion in `_get_participants_with_shares`.

---

### Case 6: CSV Semicolon Separator
**What AI did:** AI assumed `split_with` values were comma-separated.
**What was wrong:** CSV used semicolons — `"Aisha;Rohan;Priya;Meera"`.
**How I caught it:** All rows were showing "No participants found" error.
**What I changed:** Added semicolon detection:
```python
if ";" in split_with:
    names = [n.strip() for n in split_with.split(";")]
else:
    names = [n.strip() for n in split_with.split(",")]
```

---

### Case 7: Decimal and Date JSON Serialization
**What AI did:** AI stored raw parsed row data directly into `JSONField` without serialization.
**What was wrong:** Python `Decimal` and `date` objects are not JSON serializable, causing import to crash.
**How I caught it:** "Import failed: Object of type Decimal is not JSON serializable" error on first import attempt.
**What I changed:** Added `make_serializable()` helper function that converts `Decimal` to `str` and `date` to `isoformat()`.
```python
def make_serializable(data):
    if isinstance(data, dict):
        return {k: make_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [make_serializable(i) for i in data]
    elif isinstance(data, Decimal):
        return str(data)
    elif isinstance(data, (date, datetime)):
        return data.isoformat()
    return data
```