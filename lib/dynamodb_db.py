from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
import pandas as pd
import streamlit as st
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from lib.card_tags import KNOWN_CARDS, normalize_card_tag

DEFAULT_SETTINGS = {
    "monthly_income": "0",
    "current_savings": "0",
    "onhand": "0",
    "safety_buffer": "0",
}

ENTITY_PREFIXES = {
    "settings": "SETTING#",
    "bills": "BILL#",
    "income_entries": "INCOME_ENTRY#",
    "income_sources": "INCOME_SOURCE#",
    "tags": "TAG#",
    "income_bonuses": "INCOME_BONUS#",
}

ENTITY_COLUMNS = {
    "settings": ["key", "value"],
    "bills": [
        "id",
        "name",
        "bill_type",
        "base_amount",
        "conversion_fee",
        "start_month",
        "duration_months",
        "card",
        "due_day",
        "include_in_projection",
        "notes",
        "created_at",
    ],
    "income_entries": [
        "id",
        "month",
        "week_number",
        "amount",
        "notes",
        "created_at",
    ],
    "income_sources": ["id", "name", "amount", "created_at"],
    "tags": ["id", "name"],
    "income_bonuses": [
        "id",
        "name",
        "month",
        "amount",
        "notes",
        "created_at",
    ],
}

DATAFRAME_COLUMNS = {
    "bills": [
        "id",
        "name",
        "bill_type",
        "base_amount",
        "conversion_fee",
        "start_month",
        "duration_months",
        "card",
        "due_day",
        "include_in_projection",
        "notes",
    ],
    "income_entries": ["id", "month", "week_number", "amount", "notes"],
    "income_sources": ["id", "name", "amount"],
    "income_bonuses": ["id", "name", "month", "amount", "notes"],
}

MONEY_FIELDS = {"base_amount", "conversion_fee", "amount"}
INTEGER_FIELDS = {"id", "duration_months", "due_day", "week_number"}
DATE_FIELDS = {"start_month", "month"}
BOOLEAN_FIELDS = {"include_in_projection"}
COUNTER_ENTITIES = {
    "bills": "bills",
    "income_entries": "income_entries",
    "income_sources": "income_sources",
    "tags": "tags",
    "income_bonuses": "income_bonuses",
}


def _config_value(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return str(value) if value is not None else os.environ.get(name, default)


def app_partition_key() -> str:
    app_id = _config_value("DYNAMODB_APP_ID", "default")
    return f"APP#{app_id}"


@st.cache_resource(show_spinner=False)
def get_table():
    table_name = _config_value("DYNAMODB_TABLE_NAME")
    if not table_name:
        raise RuntimeError(
            "DYNAMODB_TABLE_NAME is missing. Add it to Streamlit secrets or "
            "the environment."
        )
    region = _config_value("AWS_DEFAULT_REGION") or _config_value("AWS_REGION")
    table = boto3.resource("dynamodb", region_name=region).Table(table_name)
    table.load()
    return table


def get_engine():
    return get_table()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _sort_key(entity: str, record: dict[str, Any]) -> str:
    prefix = ENTITY_PREFIXES[entity]
    if entity == "settings":
        return f"{prefix}{record['key']}"
    if entity == "tags":
        return f"{prefix}{str(record['name']).strip().casefold()}"
    if entity == "income_entries":
        month = _date_to_iso(record["month"])
        return f"{prefix}{month}#{int(record['week_number'])}"
    return f"{prefix}{int(record['id']):020d}"


def _date_to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def item_from_record(entity: str, record: dict[str, Any]) -> dict[str, Any]:
    clean_record = {
        column: record.get(column)
        for column in ENTITY_COLUMNS[entity]
        if column in record
    }
    for field in MONEY_FIELDS & clean_record.keys():
        value = clean_record[field]
        clean_record[field] = None if value is None else _decimal(value)
    for field in INTEGER_FIELDS & clean_record.keys():
        value = clean_record[field]
        clean_record[field] = None if value is None else int(value)
    for field in DATE_FIELDS & clean_record.keys():
        value = clean_record[field]
        clean_record[field] = None if value is None else _date_to_iso(value)
    for field in BOOLEAN_FIELDS & clean_record.keys():
        value = clean_record[field]
        clean_record[field] = None if value is None else bool(value)
    if "created_at" in clean_record and clean_record["created_at"] is not None:
        clean_record["created_at"] = _datetime_to_iso(clean_record["created_at"])
    return {
        "pk": app_partition_key(),
        "sk": _sort_key(entity, clean_record),
        "entity": entity,
        **clean_record,
    }


def _datetime_to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def record_from_item(entity: str, item: dict[str, Any]) -> dict[str, Any]:
    record = {column: item.get(column) for column in ENTITY_COLUMNS[entity]}
    for field in MONEY_FIELDS & record.keys():
        value = record[field]
        record[field] = None if value is None else float(value)
    for field in INTEGER_FIELDS & record.keys():
        value = record[field]
        record[field] = None if value is None else int(value)
    for field in DATE_FIELDS & record.keys():
        value = record[field]
        record[field] = None if value is None else date.fromisoformat(str(value)[:10])
    for field in BOOLEAN_FIELDS & record.keys():
        value = record[field]
        record[field] = None if value is None else bool(value)
    return record


def query_entity_records(entity: str) -> list[dict[str, Any]]:
    items = _query_items(ENTITY_PREFIXES[entity])
    return [record_from_item(entity, item) for item in items]


def export_entity_records(entity: str) -> list[dict[str, Any]]:
    items = _query_items(ENTITY_PREFIXES[entity])
    return [
        {
            column: item.get(column)
            for column in ENTITY_COLUMNS[entity]
        }
        for item in items
    ]


def _query_items(sort_key_prefix: str | None = None) -> list[dict[str, Any]]:
    table = get_table()
    key_expression = Key("pk").eq(app_partition_key())
    if sort_key_prefix:
        key_expression &= Key("sk").begins_with(sort_key_prefix)
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": key_expression,
        "ConsistentRead": True,
    }
    items: list[dict[str, Any]] = []
    while True:
        response = table.query(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def _dataframe(entity: str, sort_columns: list[str]) -> pd.DataFrame:
    columns = DATAFRAME_COLUMNS[entity]
    records = query_entity_records(entity)
    frame = pd.DataFrame(records, columns=columns)
    if frame.empty:
        return frame
    return frame.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def _next_id(entity: str) -> int:
    response = get_table().update_item(
        Key={"pk": app_partition_key(), "sk": f"COUNTER#{entity}"},
        UpdateExpression="ADD #counter_value :increment",
        ExpressionAttributeNames={"#counter_value": "value"},
        ExpressionAttributeValues={":increment": Decimal(1)},
        ReturnValues="UPDATED_NEW",
    )
    return int(response["Attributes"]["value"])


def set_counter_floor(entity: str, minimum_value: int) -> None:
    key = {"pk": app_partition_key(), "sk": f"COUNTER#{entity}"}
    table = get_table()
    current_item = table.get_item(Key=key, ConsistentRead=True).get("Item")
    current_value = int(current_item.get("value", 0)) if current_item else 0
    if current_value < minimum_value:
        table.put_item(Item={**key, "value": Decimal(minimum_value)})


def put_migrated_record(entity: str, record: dict[str, Any]) -> None:
    get_table().put_item(Item=item_from_record(entity, record))


def clear_application_items() -> int:
    items = _query_items()
    if not items:
        return 0
    table = get_table()
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
    return len(items)


def get_settings() -> dict[str, float]:
    records = query_entity_records("settings")
    values = {record["key"]: record["value"] for record in records}
    return {
        "monthly_income": total_income(),
        "current_savings": float(values.get("current_savings", 0) or 0),
        "onhand": float(values.get("onhand", 0) or 0),
        "safety_buffer": float(values.get("safety_buffer", 0) or 0),
    }


def save_settings(
    current_savings: float,
    onhand: float,
    safety_buffer: float,
) -> None:
    table = get_table()
    for key, value in {
        "current_savings": current_savings,
        "onhand": onhand,
        "safety_buffer": safety_buffer,
    }.items():
        table.put_item(
            Item=item_from_record(
                "settings",
                {"key": key, "value": str(value)},
            )
        )


def list_income_sources() -> pd.DataFrame:
    return _dataframe("income_sources", ["id"])


def total_income() -> float:
    return float(
        sum(record["amount"] or 0 for record in query_entity_records("income_sources"))
    )


def add_income_source(name: str, amount: float) -> None:
    get_table().put_item(
        Item=item_from_record(
            "income_sources",
            {
                "id": _next_id("income_sources"),
                "name": name,
                "amount": amount,
                "created_at": _now_iso(),
            },
        )
    )


def delete_income_source(source_id: int) -> None:
    _delete_by_id("income_sources", source_id)


def list_income_bonuses() -> pd.DataFrame:
    return _dataframe("income_bonuses", ["month", "id"])


def add_income_bonus(
    name: str,
    month: date,
    amount: float,
    notes: str = "",
) -> None:
    get_table().put_item(
        Item=item_from_record(
            "income_bonuses",
            {
                "id": _next_id("income_bonuses"),
                "name": name,
                "month": month,
                "amount": amount,
                "notes": notes,
                "created_at": _now_iso(),
            },
        )
    )


def delete_income_bonus(bonus_id: int) -> None:
    _delete_by_id("income_bonuses", bonus_id)


def list_bills() -> pd.DataFrame:
    return _dataframe("bills", ["start_month", "name"])


def list_card_tags() -> list[str]:
    tags = {
        record["card"]
        for record in query_entity_records("bills")
        if record.get("card")
    }
    return sorted(tags)


def add_tag(name: str) -> None:
    clean_name = name.strip()
    if not clean_name:
        return
    try:
        get_table().put_item(
            Item=item_from_record(
                "tags",
                {"id": _next_id("tags"), "name": clean_name},
            ),
            ConditionExpression="attribute_not_exists(pk)",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


def list_all_tags() -> list[str]:
    registered_tags = {
        normalize_card_tag(record["name"])
        for record in query_entity_records("tags")
        if record.get("name")
    }
    used_tags = {
        normalize_card_tag(tag)
        for tag in list_card_tags()
    }
    return sorted(
        set(KNOWN_CARDS)
        | (registered_tags - {None})
        | (used_tags - {None})
    )


def add_bill(
    name: str,
    bill_type: str,
    base_amount: float,
    conversion_fee: float,
    start_month: date,
    duration_months: int | None,
    card: str | None = None,
    due_day: int = 1,
    include_in_projection: bool = True,
    notes: str = "",
) -> int:
    bill_id = _next_id("bills")
    get_table().put_item(
        Item=item_from_record(
            "bills",
            {
                "id": bill_id,
                "name": name,
                "bill_type": bill_type,
                "base_amount": base_amount,
                "conversion_fee": conversion_fee,
                "start_month": start_month,
                "duration_months": duration_months,
                "card": card,
                "due_day": due_day,
                "include_in_projection": include_in_projection,
                "notes": notes,
                "created_at": _now_iso(),
            },
        )
    )
    return bill_id


def update_bill(bill_id: int, **fields: Any) -> None:
    if not fields:
        return
    allowed_fields = set(DATAFRAME_COLUMNS["bills"]) - {"id"}
    invalid_fields = set(fields) - allowed_fields
    if invalid_fields:
        raise ValueError(f"Unsupported bill fields: {sorted(invalid_fields)}")
    values = item_from_record("bills", {"id": bill_id, **fields})
    values.pop("pk")
    values.pop("sk")
    values.pop("entity")
    names = {f"#field_{index}": field for index, field in enumerate(values)}
    expression_values = {
        f":value_{index}": value for index, value in enumerate(values.values())
    }
    assignments = ", ".join(
        f"{name} = :value_{index}"
        for index, name in enumerate(names)
    )
    get_table().update_item(
        Key={
            "pk": app_partition_key(),
            "sk": _sort_key("bills", {"id": bill_id}),
        },
        UpdateExpression=f"SET {assignments}",
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=expression_values,
        ConditionExpression="attribute_exists(pk)",
    )


def delete_bill(bill_id: int) -> None:
    _delete_by_id("bills", bill_id)


def list_income_entries() -> pd.DataFrame:
    return _dataframe("income_entries", ["month", "week_number"])


def upsert_income_entry(
    month: date,
    week_number: int,
    amount: float,
    notes: str = "",
) -> None:
    table = get_table()
    key_record = {"month": month, "week_number": week_number}
    key = {
        "pk": app_partition_key(),
        "sk": _sort_key("income_entries", key_record),
    }
    existing = table.get_item(Key=key, ConsistentRead=True).get("Item")
    entry_id = int(existing["id"]) if existing else _next_id("income_entries")
    table.put_item(
        Item=item_from_record(
            "income_entries",
            {
                "id": entry_id,
                "month": month,
                "week_number": week_number,
                "amount": amount,
                "notes": notes,
                "created_at": existing.get("created_at", _now_iso())
                if existing
                else _now_iso(),
            },
        )
    )


def delete_income_entry(entry_id: int) -> None:
    matching_record = next(
        (
            record
            for record in query_entity_records("income_entries")
            if record["id"] == entry_id
        ),
        None,
    )
    if not matching_record:
        return
    get_table().delete_item(
        Key={
            "pk": app_partition_key(),
            "sk": _sort_key("income_entries", matching_record),
        }
    )


def _delete_by_id(entity: str, record_id: int) -> None:
    get_table().delete_item(
        Key={
            "pk": app_partition_key(),
            "sk": _sort_key(entity, {"id": record_id}),
        }
    )
