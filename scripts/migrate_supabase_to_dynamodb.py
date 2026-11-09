from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib import dynamodb_db

SOURCE_QUERIES = {
    "settings": "SELECT key, value FROM settings",
    "bills": (
        "SELECT id, name, bill_type, base_amount, conversion_fee, start_month, "
        "duration_months, card, due_day, include_in_projection, notes, created_at "
        "FROM bills"
    ),
    "income_entries": (
        "SELECT id, month, week_number, amount, notes, created_at "
        "FROM income_entries"
    ),
    "income_sources": (
        "SELECT id, name, amount, created_at FROM income_sources"
    ),
    "tags": "SELECT id, name FROM tags",
    "income_bonuses": (
        "SELECT id, name, month, amount, notes, created_at FROM income_bonuses"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export Supabase/Postgres records, migrate them to DynamoDB, and "
            "verify deterministic row counts and hashes."
        )
    )
    parser.add_argument(
        "--source-db-url",
        default=os.environ.get("DB_URL"),
        help="Supabase Postgres connection string. Defaults to DB_URL.",
    )
    parser.add_argument(
        "--table-name",
        default=os.environ.get("DYNAMODB_TABLE_NAME"),
        help="Destination DynamoDB table. Defaults to DYNAMODB_TABLE_NAME.",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-2"),
        help="AWS region containing the table.",
    )
    parser.add_argument(
        "--app-id",
        default=os.environ.get("DYNAMODB_APP_ID", "default"),
        help="Logical app partition identifier.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "migration_backups",
        help="Private local directory for JSON exports and manifests.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Export and validate Supabase without writing to DynamoDB.",
    )
    mode.add_argument(
        "--verify-only",
        action="store_true",
        help="Compare Supabase with the existing DynamoDB data without writing.",
    )
    parser.add_argument(
        "--replace-target",
        action="store_true",
        help=(
            "Delete this app partition from DynamoDB before import. Use during "
            "the final maintenance window so removed Supabase rows cannot remain."
        ),
    )
    return parser.parse_args()


def normalized_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def read_source_records(database_url: str) -> dict[str, list[dict[str, Any]]]:
    engine = create_engine(normalized_postgres_url(database_url), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            return {
                entity: [
                    dict(row)
                    for row in connection.execute(text(query)).mappings().all()
                ]
                for entity, query in SOURCE_QUERIES.items()
            }
    finally:
        engine.dispose()


def canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, datetime):
        normalized = value
        if normalized.tzinfo is None:
            normalized = normalized.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, Decimal, float)):
        decimal_value = Decimal(str(value))
        if decimal_value == decimal_value.to_integral():
            return format(decimal_value.quantize(Decimal(1)), "f")
        return format(decimal_value.normalize(), "f")
    return str(value)


def canonical_records(
    records_by_entity: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    canonical: dict[str, list[dict[str, Any]]] = {}
    for entity, records in records_by_entity.items():
        columns = dynamodb_db.ENTITY_COLUMNS[entity]
        normalized_records = [
            {
                column: canonical_value(record.get(column))
                for column in columns
            }
            for record in records
        ]
        canonical[entity] = sorted(
            normalized_records,
            key=lambda record: json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
    return canonical


def build_manifest(
    records_by_entity: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    canonical = canonical_records(records_by_entity)
    manifest: dict[str, dict[str, Any]] = {}
    for entity, records in canonical.items():
        encoded = json.dumps(
            records,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        manifest[entity] = {
            "count": len(records),
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }
    return manifest


def write_export(
    output_directory: Path,
    source_records: dict[str, list[dict[str, Any]]],
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    export_path = output_directory / f"supabase-export-{timestamp}.json"
    manifest_path = output_directory / f"supabase-manifest-{timestamp}.json"
    export_path.write_text(
        json.dumps(
            canonical_records(source_records),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(build_manifest(source_records), indent=2),
        encoding="utf-8",
    )
    return export_path, manifest_path


def read_destination_records() -> dict[str, list[dict[str, Any]]]:
    return {
        entity: dynamodb_db.export_entity_records(entity)
        for entity in SOURCE_QUERIES
    }


def import_records(
    source_records: dict[str, list[dict[str, Any]]],
    replace_target: bool,
) -> None:
    if replace_target:
        deleted_count = dynamodb_db.clear_application_items()
        print(f"Cleared {deleted_count} existing DynamoDB items.")

    table = dynamodb_db.get_table()
    with table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
        for entity, records in source_records.items():
            for record in records:
                batch.put_item(
                    Item=dynamodb_db.item_from_record(entity, record)
                )

    for entity, counter_name in dynamodb_db.COUNTER_ENTITIES.items():
        maximum_id = max(
            (
                int(record["id"])
                for record in source_records[entity]
                if record.get("id") is not None
            ),
            default=0,
        )
        dynamodb_db.set_counter_floor(counter_name, maximum_id)


def verify_records(
    source_records: dict[str, list[dict[str, Any]]],
    destination_records: dict[str, list[dict[str, Any]]],
) -> bool:
    source_manifest = build_manifest(source_records)
    destination_manifest = build_manifest(destination_records)
    verified = True
    for entity in SOURCE_QUERIES:
        source_result = source_manifest[entity]
        destination_result = destination_manifest[entity]
        matches = source_result == destination_result
        verified = verified and matches
        status = "MATCH" if matches else "MISMATCH"
        print(
            f"{status:8} {entity:16} "
            f"source={source_result['count']} "
            f"destination={destination_result['count']}"
        )
        if not matches:
            print(f"         source SHA-256:      {source_result['sha256']}")
            print(
                f"         destination SHA-256: "
                f"{destination_result['sha256']}"
            )
    return verified


def configure_destination(args: argparse.Namespace) -> None:
    if not args.table_name:
        raise ValueError(
            "DynamoDB table name is missing. Pass --table-name or set "
            "DYNAMODB_TABLE_NAME."
        )
    os.environ["DYNAMODB_TABLE_NAME"] = args.table_name
    os.environ["AWS_DEFAULT_REGION"] = args.region
    os.environ["DYNAMODB_APP_ID"] = args.app_id


def main() -> int:
    args = parse_args()
    if not args.source_db_url:
        print(
            "Supabase connection string is missing. Pass --source-db-url or "
            "set DB_URL.",
            file=sys.stderr,
        )
        return 2

    print("Reading the authoritative Supabase database...")
    source_records = read_source_records(args.source_db_url)
    export_path, manifest_path = write_export(args.output_dir, source_records)
    print(f"Private JSON export: {export_path}")
    print(f"Verification manifest: {manifest_path}")

    if args.dry_run:
        print("Dry run complete. DynamoDB was not accessed or changed.")
        return 0

    try:
        configure_destination(args)
        dynamodb_db.get_table.clear()
        if not args.verify_only:
            import_records(source_records, args.replace_target)
        destination_records = read_destination_records()
    except Exception as error:
        print(f"DynamoDB operation failed: {error}", file=sys.stderr)
        return 2

    if not verify_records(source_records, destination_records):
        print("Verification failed. Do not switch the production backend.")
        return 1

    print("Verification passed: every entity count and SHA-256 hash matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
