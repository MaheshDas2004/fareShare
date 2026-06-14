from decimal import Decimal
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib import admin
from django.test import RequestFactory, SimpleTestCase, TestCase

from authentication.models import User
from expenses.admin import ExpenseAdmin
from expenses.models import Currency, Expense, ExpenseParticipant, ExpenseSplit
from groups.models import Group
from expenses.services.split_logic import SplitLogic


class FakeParticipant:
    def __init__(self, user, share=None, is_included=True):
        self.user = user
        self.share = share
        self.is_included = is_included


class FakeParticipantCollection(list):
    def exists(self):
        return bool(self)

    def count(self):
        return len(self)


class FakeParticipantManager:
    def __init__(self, participants):
        self._participants = participants

    def filter(self, **kwargs):
        included = kwargs.get("is_included")
        if included is True:
            return FakeParticipantCollection(
                [p for p in self._participants if p.is_included]
            )

        if included is False:
            return FakeParticipantCollection(
                [p for p in self._participants if not p.is_included]
            )

        return FakeParticipantCollection(self._participants)


def build_expense(amount, split_type, participants):
    return SimpleNamespace(
        amount=Decimal(amount),
        split_type=split_type,
        participants=FakeParticipantManager(participants),
    )


class SplitLogicTests(SimpleTestCase):
    def setUp(self):
        self.engine = SplitLogic()
        self.users = [SimpleNamespace(id=i, username=f"user{i}") for i in range(1, 5)]

    @patch("expenses.services.split_logic.ExpenseSplit.objects.update_or_create")
    def test_equal_split_ignores_excluded_participant(self, mock_update_or_create):
        participants = [
            FakeParticipant(self.users[0]),
            FakeParticipant(self.users[1]),
            FakeParticipant(self.users[2]),
            FakeParticipant(self.users[3], is_included=False),
        ]
        expense = build_expense("120.00", "EQUAL", participants)

        splits = self.engine.calculate(expense)

        self.assertEqual(len(splits), 3)
        self.assertEqual(
            [split["amount"] for split in splits],
            [Decimal("40.00"), Decimal("40.00"), Decimal("40.00")],
        )
        self.assertNotIn(self.users[3], [split["user"] for split in splits])
        self.assertEqual(mock_update_or_create.call_count, 3)

    @patch("expenses.services.split_logic.ExpenseSplit.objects.update_or_create")
    def test_unequal_split_uses_explicit_amounts(self, mock_update_or_create):
        participants = [
            FakeParticipant(self.users[0], share=Decimal("10.00")),
            FakeParticipant(self.users[1], share=Decimal("20.00")),
            FakeParticipant(self.users[2], share=Decimal("30.00")),
            FakeParticipant(self.users[3], share=Decimal("60.00")),
        ]
        expense = build_expense("120.00", "UNEQUAL", participants)

        splits = self.engine.calculate(expense)

        self.assertEqual(
            [split["amount"] for split in splits],
            [Decimal("10.00"), Decimal("20.00"), Decimal("30.00"), Decimal("60.00")],
        )
        self.assertEqual(mock_update_or_create.call_count, 4)

    @patch("expenses.services.split_logic.ExpenseSplit.objects.update_or_create")
    def test_percent_split_calculates_from_percentages(self, mock_update_or_create):
        participants = [
            FakeParticipant(self.users[0], share=Decimal("25")),
            FakeParticipant(self.users[1], share=Decimal("25")),
            FakeParticipant(self.users[2], share=Decimal("25")),
            FakeParticipant(self.users[3], share=Decimal("25")),
        ]
        expense = build_expense("120.00", "PERCENT", participants)

        splits = self.engine.calculate(expense)

        self.assertEqual(
            [split["amount"] for split in splits],
            [Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("30.00")],
        )
        self.assertEqual(mock_update_or_create.call_count, 4)

    @patch("expenses.services.split_logic.ExpenseSplit.objects.update_or_create")
    def test_shares_split_distributes_by_weight(self, mock_update_or_create):
        participants = [
            FakeParticipant(self.users[0], share=Decimal("1")),
            FakeParticipant(self.users[1], share=Decimal("1")),
            FakeParticipant(self.users[2], share=Decimal("2")),
            FakeParticipant(self.users[3], share=Decimal("2")),
        ]
        expense = build_expense("120.00", "SHARES", participants)

        splits = self.engine.calculate(expense)

        self.assertEqual(
            [split["amount"] for split in splits],
            [Decimal("20.00"), Decimal("20.00"), Decimal("40.00"), Decimal("40.00")],
        )
        self.assertEqual(mock_update_or_create.call_count, 4)


class ExpenseAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = ExpenseAdmin(Expense, admin.site)
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="testpass123",
        )
        self.currency = Currency.objects.create(code="INR", name="Indian Rupee", symbol="₹")
        self.group = Group.objects.create(
            name="Trip",
            description="Trip expenses",
            created_by=self.owner,
        )
        self.users = [
            self.owner,
            User.objects.create_user(username="u2", email="u2@example.com", password="testpass123"),
            User.objects.create_user(username="u3", email="u3@example.com", password="testpass123"),
            User.objects.create_user(username="u4", email="u4@example.com", password="testpass123"),
        ]

    def test_admin_save_related_creates_expense_splits(self):
        expense = Expense.objects.create(
            group=self.group,
            description="Dinner",
            amount=Decimal("120.00"),
            currency=self.currency,
            paid_by=self.owner,
            split_type="EQUAL",
            date=date(2026, 6, 14),
            created_by=self.owner,
        )
        for user in self.users:
            ExpenseParticipant.objects.create(expense=expense, user=user, is_included=True)

        request = self.factory.post("/admin/expenses/expense/add/")

        class DummyForm:
            def __init__(self, instance):
                self.instance = instance

            def save_m2m(self):
                return None

        self.admin.save_related(request, DummyForm(expense), [], change=False)

        self.assertEqual(ExpenseSplit.objects.filter(expense=expense).count(), 4)
        self.assertEqual(
            list(ExpenseSplit.objects.filter(expense=expense).order_by("user_id").values_list("owed_amount", flat=True)),
            [Decimal("30.00"), Decimal("30.00"), Decimal("30.00"), Decimal("30.00")],
        )
