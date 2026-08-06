"""Diffing logic for the editable bills table on Manage bills.

Split out from the view as a pure function (no Streamlit, no DB) so it's
directly unit-testable — Streamlit's AppTest can't simulate edits inside a
st.data_editor, so this is the only way to verify the reconciliation logic
without a live browser.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class BillsDiff:
    deletes: list[int] = field(default_factory=list)
    adds: list[dict] = field(default_factory=list)      # kwargs ready for db.add_bill
    updates: list[tuple[int, dict]] = field(default_factory=list)  # (id, kwargs) ready for db.update_bill
    skipped: int = 0


def _clean_str(v) -> str:
    return str(v).strip() if pd.notna(v) else ""


def _clean_amount(v) -> float:
    return float(v) if pd.notna(v) else 0.0


def _clean_int(v) -> int | None:
    return int(v) if pd.notna(v) else None


def _clean_card(v) -> str | None:
    s = _clean_str(v)
    return s or None


def _to_month_start(v) -> date:
    return date(v.year, v.month, 1)


def diff_bills_edit(original_df: pd.DataFrame, edited_df: pd.DataFrame) -> BillsDiff:
    """Compare the table as loaded from the DB (`original_df`, must include
    `id`) against what st.data_editor returned (`edited_df`, same columns —
    new rows have a NaN `id`), and produce the delete/add/update operations
    needed to make the DB match what's on screen."""
    diff = BillsDiff()
    original_by_id = original_df.set_index("id")
    original_ids = set(original_by_id.index)
    edited_ids = {int(v) for v in edited_df["id"].dropna()}

    diff.deletes = sorted(original_ids - edited_ids)

    for _, row in edited_df.iterrows():
        if pd.notna(row["id"]):
            continue
        name, bill_type, start = _clean_str(row["name"]), row["bill_type"], row["start_month"]
        if not name or not bill_type or not row["base_amount"] or pd.isna(start):
            diff.skipped += 1
            continue
        diff.adds.append({
            "name": name,
            "bill_type": bill_type,
            "base_amount": _clean_amount(row["base_amount"]),
            "conversion_fee": _clean_amount(row["conversion_fee"]),
            "start_month": _to_month_start(start),
            "duration_months": _clean_int(row["duration_months"]),
            "card": _clean_card(row["card"]),
            "due_day": _clean_int(row["due_day"]) or 1,
            "include_in_projection": bool(row["include_in_projection"]) if pd.notna(row["include_in_projection"]) else True,
            "notes": _clean_str(row["notes"]),
        })

    for _, row in edited_df.iterrows():
        if pd.isna(row["id"]) or int(row["id"]) not in original_by_id.index:
            continue
        bill_id = int(row["id"])
        orig = original_by_id.loc[bill_id]
        fields = {}

        for col in ["base_amount", "conversion_fee"]:
            new_val = _clean_amount(row[col])
            if round(new_val, 2) != round(float(orig[col]), 2):
                fields[col] = new_val

        new_due_day = _clean_int(row["due_day"]) or 1
        if new_due_day != int(orig["due_day"]):
            fields["due_day"] = new_due_day

        new_start = _to_month_start(row["start_month"])
        if new_start != _to_month_start(orig["start_month"]):
            fields["start_month"] = new_start

        new_duration = _clean_int(row["duration_months"])
        orig_duration = _clean_int(orig["duration_months"])
        if new_duration != orig_duration:
            fields["duration_months"] = new_duration

        new_card = _clean_card(row["card"])
        orig_card = _clean_card(orig["card"])
        if new_card != orig_card:
            fields["card"] = new_card

        new_include = bool(row["include_in_projection"]) if pd.notna(row["include_in_projection"]) else True
        if new_include != bool(orig["include_in_projection"]):
            fields["include_in_projection"] = new_include

        new_notes = _clean_str(row["notes"])
        if new_notes != _clean_str(orig["notes"]):
            fields["notes"] = new_notes

        # name/bill_type are NOT NULL in the DB — never write an empty
        # string over them, just leave that field alone if cleared.
        new_name = _clean_str(row["name"])
        if new_name and new_name != _clean_str(orig["name"]):
            fields["name"] = new_name
        new_type = _clean_str(row["bill_type"])
        if new_type and new_type != _clean_str(orig["bill_type"]):
            fields["bill_type"] = new_type

        if fields:
            diff.updates.append((bill_id, fields))

    return diff
