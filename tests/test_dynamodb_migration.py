from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from lib import dynamodb_db
from scripts.migrate_supabase_to_dynamodb import build_manifest


class DynamoDbRecordMappingTests(unittest.TestCase):
    def test_bill_round_trip_preserves_identifiers_dates_and_money(self) -> None:
        source = {
            "id": 42,
            "name": "Internet",
            "bill_type": "recurring",
            "base_amount": Decimal("1499.50"),
            "conversion_fee": Decimal("0.00"),
            "start_month": date(2026, 11, 1),
            "duration_months": None,
            "card": None,
            "due_day": 12,
            "include_in_projection": True,
            "notes": "",
            "created_at": datetime(2026, 11, 9, tzinfo=timezone.utc),
        }

        with patch.object(
            dynamodb_db,
            "app_partition_key",
            return_value="APP#test",
        ):
            item = dynamodb_db.item_from_record("bills", source)

        self.assertEqual(item["pk"], "APP#test")
        self.assertEqual(item["sk"], "BILL#00000000000000000042")
        self.assertEqual(item["base_amount"], Decimal("1499.50"))
        self.assertEqual(item["start_month"], "2026-11-01")

        restored = dynamodb_db.record_from_item("bills", item)
        self.assertEqual(restored["id"], 42)
        self.assertEqual(restored["base_amount"], 1499.5)
        self.assertEqual(restored["start_month"], date(2026, 11, 1))
        self.assertIsNone(restored["duration_months"])

    def test_income_entry_key_enforces_month_and_week_uniqueness(self) -> None:
        first_record = {
            "id": 1,
            "month": date(2026, 11, 1),
            "week_number": 2,
            "amount": 1000,
            "notes": "",
            "created_at": datetime.now(timezone.utc),
        }
        replacement_record = {**first_record, "id": 99, "amount": 1200}

        with patch.object(
            dynamodb_db,
            "app_partition_key",
            return_value="APP#test",
        ):
            first_item = dynamodb_db.item_from_record(
                "income_entries",
                first_record,
            )
            replacement_item = dynamodb_db.item_from_record(
                "income_entries",
                replacement_record,
            )

        self.assertEqual(first_item["sk"], replacement_item["sk"])
        self.assertEqual(first_item["sk"], "INCOME_ENTRY#2026-11-01#2")


class MigrationManifestTests(unittest.TestCase):
    def test_equivalent_postgres_and_dynamodb_values_have_same_hash(self) -> None:
        timestamp = datetime(2026, 11, 9, 3, 30, tzinfo=timezone.utc)
        source = {
            "settings": [{"key": "current_savings", "value": "10000"}],
            "bills": [
                {
                    "id": 1,
                    "name": "Rent",
                    "bill_type": "recurring",
                    "base_amount": Decimal("8000.00"),
                    "conversion_fee": Decimal("0"),
                    "start_month": date(2026, 11, 1),
                    "duration_months": None,
                    "card": None,
                    "due_day": 1,
                    "include_in_projection": True,
                    "notes": "",
                    "created_at": timestamp,
                }
            ],
            "income_entries": [],
            "income_sources": [],
            "tags": [],
            "income_bonuses": [],
        }
        destination = {
            **source,
            "bills": [
                {
                    **source["bills"][0],
                    "id": Decimal("1"),
                    "base_amount": 8000.0,
                    "conversion_fee": 0.0,
                    "due_day": Decimal("1"),
                    "created_at": timestamp.isoformat(),
                }
            ],
        }

        self.assertEqual(build_manifest(source), build_manifest(destination))


if __name__ == "__main__":
    unittest.main()
