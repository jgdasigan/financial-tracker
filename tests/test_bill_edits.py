from __future__ import annotations

import unittest
from datetime import date

import pandas as pd

from lib.bill_edits import (
    filter_bills,
    is_completed_bill,
    original_update_fields,
)


class CompletedBillTests(unittest.TestCase):
    def test_archives_after_final_payment_month(self) -> None:
        bill = {
            "bill_type": "installment",
            "start_month": date(2026, 1, 1),
            "duration_months": 3,
        }

        self.assertTrue(
            is_completed_bill(bill, current_month=date(2026, 4, 1))
        )

    def test_remains_current_during_final_payment_month(self) -> None:
        bill = {
            "bill_type": "installment",
            "start_month": date(2026, 1, 1),
            "duration_months": 3,
        }

        self.assertFalse(
            is_completed_bill(bill, current_month=date(2026, 3, 1))
        )

    def test_archives_one_time_and_pakaskas_bills(self) -> None:
        one_time = {
            "bill_type": "onetime",
            "start_month": date(2026, 1, 1),
            "duration_months": 1,
        }
        pakaskas = {
            "bill_type": "pakaskas",
            "start_month": date(2026, 1, 1),
            "duration_months": 2,
        }

        self.assertTrue(
            is_completed_bill(one_time, current_month=date(2026, 2, 1))
        )
        self.assertTrue(
            is_completed_bill(pakaskas, current_month=date(2026, 3, 1))
        )

    def test_keeps_ongoing_recurring_bill_current(self) -> None:
        bill = {
            "bill_type": "recurring",
            "start_month": date(2026, 1, 1),
            "duration_months": None,
        }

        self.assertFalse(
            is_completed_bill(bill, current_month=date(2026, 4, 1))
        )

    def test_archives_finite_recurring_bill(self) -> None:
        bill = {
            "bill_type": "recurring",
            "start_month": date(2026, 1, 1),
            "duration_months": 2,
        }

        self.assertTrue(
            is_completed_bill(bill, current_month=date(2026, 3, 1))
        )


class BillUndoTests(unittest.TestCase):
    def test_original_update_fields_normalizes_database_values(self) -> None:
        record = {
            "name": "Internet",
            "bill_type": "recurring",
            "base_amount": 1499,
            "conversion_fee": 0,
            "start_month": date(2026, 1, 12),
            "duration_months": None,
            "card": None,
            "due_day": 5,
            "include_in_projection": True,
            "notes": None,
        }

        self.assertEqual(
            original_update_fields(
                record,
                {"base_amount", "card", "notes", "start_month"},
            ),
            {
                "base_amount": 1499.0,
                "card": None,
                "notes": "",
                "start_month": date(2026, 1, 1),
            },
        )


class BillFilterTests(unittest.TestCase):
    def test_filters_by_scheduled_month_type_and_name(self) -> None:
        bills = pd.DataFrame(
            [
                {
                    "name": "Zeta recurring",
                    "bill_type": "recurring",
                    "base_amount": 100,
                    "conversion_fee": 0,
                    "start_month": date(2026, 1, 1),
                    "duration_months": None,
                },
                {
                    "name": "Alpha one-time",
                    "bill_type": "onetime",
                    "base_amount": 200,
                    "conversion_fee": 0,
                    "start_month": date(2026, 3, 1),
                    "duration_months": 1,
                },
                {
                    "name": "Middle installment",
                    "bill_type": "installment",
                    "base_amount": 300,
                    "conversion_fee": 0,
                    "start_month": date(2026, 2, 1),
                    "duration_months": 2,
                },
            ]
        )

        march_bills = filter_bills(
            bills,
            selected_month=date(2026, 3, 1),
        )
        self.assertEqual(
            march_bills["name"].tolist(),
            ["Alpha one-time"],
        )

        installments = filter_bills(
            bills,
            selected_type="installment",
        )
        self.assertEqual(
            installments["name"].tolist(),
            ["Middle installment"],
        )

        alphabetical = filter_bills(bills, alphabetical=True)
        self.assertEqual(
            alphabetical["name"].tolist(),
            [
                "Alpha one-time",
                "Middle installment",
                "Zeta recurring",
            ],
        )


if __name__ == "__main__":
    unittest.main()
