from __future__ import annotations

import unittest
from datetime import date

from lib.calculations import bill_due_date, bills_due_between, card_due_by_month


def recurring_bill(due_day: int) -> dict:
    return {
        "name": f"Due day {due_day}",
        "bill_type": "recurring",
        "base_amount": 100,
        "conversion_fee": 0,
        "start_month": date(2026, 1, 1),
        "duration_months": None,
        "due_day": due_day,
    }


class UpcomingPaymentTests(unittest.TestCase):
    def test_clamps_due_day_to_final_day_of_month(self) -> None:
        self.assertEqual(
            bill_due_date(recurring_bill(31), date(2026, 2, 1)),
            date(2026, 2, 28),
        )

    def test_calendar_week_can_span_two_months(self) -> None:
        payments = bills_due_between(
            [recurring_bill(31), recurring_bill(1)],
            date(2026, 8, 31),
            date(2026, 9, 6),
        )

        self.assertEqual(
            [payment[0] for payment in payments],
            [date(2026, 8, 31), date(2026, 9, 1)],
        )


class CardTagTests(unittest.TestCase):
    def test_known_card_aliases_share_dashboard_totals(self) -> None:
        month = date(2026, 11, 1)
        bills = [
            {
                **recurring_bill(1),
                "card": "maribank cc",
                "base_amount": 100,
            },
            {
                **recurring_bill(1),
                "card": "TIKTOK PAYLATER",
                "base_amount": 200,
            },
            {
                **recurring_bill(1),
                "card": "Spaylater",
                "base_amount": 300,
            },
        ]

        self.assertEqual(
            card_due_by_month(bills, "Maribank CC", [month]),
            [100],
        )
        self.assertEqual(
            card_due_by_month(bills, "Tiktok PayLater", [month]),
            [200],
        )
        self.assertEqual(
            card_due_by_month(bills, "Shopee PayLater", [month]),
            [300],
        )


if __name__ == "__main__":
    unittest.main()
