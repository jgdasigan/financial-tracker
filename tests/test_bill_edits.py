from __future__ import annotations

import unittest
from datetime import date

from lib.bill_edits import is_completed_bill


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


if __name__ == "__main__":
    unittest.main()
