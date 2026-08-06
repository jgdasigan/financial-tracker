"""Schedule building, savings projection, and affordability math.

Pure functions, no Streamlit/DB imports here, so this is easy to unit-test
and to reuse from both the dashboard and the affordability checker.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

BillDict = dict  # {name, bill_type, base_amount, conversion_fee, start_month, duration_months}


def add_months(d: date, n: int) -> date:
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1)


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def month_label(d: date) -> str:
    return d.strftime("%b %Y")


def month_range(start: date, n_months: int) -> list[date]:
    return [add_months(start, i) for i in range(n_months)]


# Weekly payroll buckets within a month — days 1-7 / 8-14 / 15-21 / 22-end,
# matching the common semi-weekly "1st wk / 2nd wk / 3rd wk / 4th wk" payroll
# convention rather than ISO calendar weeks.
WEEK_DAY_RANGES = {1: (1, 7), 2: (8, 14), 3: (15, 21), 4: (22, 31)}


def week_of_month(day: int) -> int:
    if day <= 7:
        return 1
    if day <= 14:
        return 2
    if day <= 21:
        return 3
    return 4


def week_label(month: date, week_number: int) -> str:
    ordinal = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}[week_number]
    return f"{ordinal} wk, {month_label(month)}"


def bills_due_in_week(bills: list[BillDict], month: date, week_number: int) -> list[tuple[BillDict, float]]:
    """Bills active in `month` whose due_day falls in that week bucket."""
    target = month_start(month)
    due = []
    for bill in bills:
        amt = bill_amount_for_month(bill, target)
        if not amt:
            continue
        if week_of_month(int(bill.get("due_day") or 1)) == week_number:
            due.append((bill, amt))
    return due


def card_tag(bill: BillDict) -> str | None:
    """A bill's card/tag, normalized to a real string or None. Untagged rows
    come back from Postgres as NaN (a float) rather than None once read
    through pandas, and NaN is truthy in Python — `if bill.get("card")` would
    silently treat "no tag" as "has a tag" and blow up ordering/grouping."""
    card = bill.get("card")
    return card if isinstance(card, str) and card else None


def _duration_or_none(duration) -> int | None:
    """Normalize a duration that may come in as None, NaN (from a SQL NULL
    read through pandas), or a float/int, into a clean int or None."""
    if duration is None:
        return None
    if isinstance(duration, float) and pd.isna(duration):
        return None
    return int(duration)


def bill_amount_for_month(bill: BillDict, month: date) -> float | None:
    """Amount due for `bill` in `month`, or None if the bill doesn't apply."""
    start = month_start(bill["start_month"])
    if month < start:
        return None

    bill_type = bill["bill_type"]
    duration = _duration_or_none(bill.get("duration_months"))

    if bill_type == "onetime":
        return float(bill["base_amount"]) if month == start else None

    if bill_type in ("installment", "pakaskas"):
        # Pakaskas (lending to someone else / fronting a reimbursable
        # payment) follows the exact same monthly-amount-for-N-months shape
        # as an installment — it's just tracked separately and can opt out
        # of the leftover/savings math via include_in_projection.
        span = duration or 1
        idx = _month_diff(start, month)
        if idx < 0 or idx >= span:
            return None
        fee = float(bill.get("conversion_fee") or 0) if idx == 0 else 0.0
        return float(bill["base_amount"]) + fee

    if bill_type == "recurring":
        idx = _month_diff(start, month)
        if idx < 0:
            return None
        if duration is not None and idx >= duration:
            return None
        return float(bill["base_amount"])

    raise ValueError(f"Unknown bill_type: {bill_type}")


def _month_diff(start: date, month: date) -> int:
    return (month.year - start.year) * 12 + (month.month - start.month)


def build_schedule(bills: list[BillDict], horizon_start: date, n_months: int) -> tuple[pd.DataFrame, list[date]]:
    """Pivoted schedule: rows = bill name, columns = month label, values = amount due.

    Mirrors the handwritten "Payments Schedule" table: one row per item, one
    column per month, blank where a bill isn't active that month.
    """
    months = month_range(month_start(horizon_start), n_months)
    labels = [month_label(m) for m in months]

    data = {}
    for bill in bills:
        row = {}
        for m, lbl in zip(months, labels):
            amt = bill_amount_for_month(bill, m)
            if amt is not None:
                row[lbl] = row.get(lbl, 0.0) + amt
        data[bill["name"]] = row

    df = pd.DataFrame.from_dict(data, orient="index")
    df = df.reindex(columns=labels)
    return df, months


def remaining_amount(bill: BillDict, as_of_month: date) -> float:
    """Total still scheduled for `bill` from `as_of_month` onward. Meant for
    finite bills (installment/onetime) — a still-ongoing recurring bill has
    no defined end, so "remaining" isn't a meaningful question for it."""
    start = month_start(bill["start_month"])
    duration = _duration_or_none(bill.get("duration_months")) or 1
    cutoff = month_start(as_of_month)
    total = 0.0
    for i in range(duration):
        m = add_months(start, i)
        if m >= cutoff:
            total += bill_amount_for_month(bill, m) or 0.0
    return total


def card_due_by_month(bills: list[BillDict], tag: str, months: list[date]) -> list[float]:
    """The amount actually charged to `tag` (a card/tag name) in each month
    in `months` — i.e. bill_amount_for_month() summed across that card's
    installment/pakaskas bills. This is the payment due that month, not a
    running remaining-balance total.

    Pakaskas counts here *regardless* of include_in_projection: whether the
    money is "yours" or not is a separate question from whether the card
    bill itself is due — you still have to pay the card either way."""
    relevant = [b for b in bills if b["bill_type"] in ("installment", "pakaskas") and card_tag(b) == tag]
    return [sum(bill_amount_for_month(b, m) or 0.0 for b in relevant) for m in months]


def monthly_totals(schedule_df: pd.DataFrame) -> pd.Series:
    if schedule_df.empty:
        return pd.Series(dtype=float)
    return schedule_df.sum(axis=0, skipna=True)


def sum_bonuses_by_month(bonuses: list[dict]) -> dict[date, float]:
    """Turn income_bonus rows (each with `month` and `amount`) into the
    {month_start: total} shape project_savings()/check_affordability() want,
    summing if more than one bonus lands in the same month."""
    totals: dict[date, float] = {}
    for b in bonuses:
        m = month_start(b["month"])
        totals[m] = totals.get(m, 0.0) + float(b["amount"])
    return totals


def project_savings(
    totals: pd.Series,
    months: list[date],
    monthly_income: float,
    starting_savings: float,
    extra_income: dict[date, float] | None = None,
) -> pd.DataFrame:
    """Month-by-month leftover and running savings balance.

    `extra_income` is a one-off bump for specific months (a December bonus,
    a tax refund, ...) on top of the recurring `monthly_income` — keyed by
    the first-of-month date, e.g. {date(2026, 12, 1): 20000.0}."""
    extra_income = extra_income or {}
    rows = []
    running = starting_savings
    for m in months:
        lbl = month_label(m)
        total_bills = float(totals.get(lbl, 0.0) or 0.0)
        bonus = float(extra_income.get(month_start(m), 0.0))
        income_this_month = monthly_income + bonus
        leftover = income_this_month - total_bills
        running += leftover
        rows.append(
            {
                "month": lbl,
                "income": income_this_month,
                "total_bills": total_bills,
                "leftover": leftover,
                "savings_balance": running,
            }
        )
    return pd.DataFrame(rows)


@dataclass
class AffordabilityResult:
    before: pd.DataFrame
    after: pd.DataFrame
    comparison: pd.DataFrame
    affordable: bool
    first_shortfall_month: str | None
    worst_shortfall: float


def check_affordability(
    existing_bills: list[BillDict],
    proposed_bill: BillDict,
    horizon_start: date,
    n_months: int,
    monthly_income: float,
    starting_savings: float,
    safety_buffer: float = 0.0,
    extra_income: dict[date, float] | None = None,
) -> AffordabilityResult:
    """Compare projected leftover/savings with vs. without the proposed bill."""
    before_schedule, months = build_schedule(existing_bills, horizon_start, n_months)
    before_totals = monthly_totals(before_schedule)
    before = project_savings(before_totals, months, monthly_income, starting_savings, extra_income)

    after_schedule, _ = build_schedule(existing_bills + [proposed_bill], horizon_start, n_months)
    after_totals = monthly_totals(after_schedule)
    after = project_savings(after_totals, months, monthly_income, starting_savings, extra_income)

    comparison = pd.DataFrame(
        {
            "month": before["month"],
            "leftover_before": before["leftover"],
            "leftover_after": after["leftover"],
            "savings_balance_after": after["savings_balance"],
        }
    )
    comparison["shortfall"] = safety_buffer - comparison["leftover_after"]
    comparison["affordable"] = comparison["leftover_after"] >= safety_buffer

    shortfalls = comparison[~comparison["affordable"]]
    affordable = shortfalls.empty
    first_shortfall_month = None if affordable else shortfalls.iloc[0]["month"]
    worst_shortfall = 0.0 if affordable else float(shortfalls["shortfall"].max())

    return AffordabilityResult(
        before=before,
        after=after,
        comparison=comparison,
        affordable=affordable,
        first_shortfall_month=first_shortfall_month,
        worst_shortfall=worst_shortfall,
    )


@dataclass
class CashAffordabilityResult:
    savings_before: float
    savings_after: float
    affordable: bool
    shortfall: float


def check_cash_affordability(
    current_savings: float,
    price: float,
    safety_buffer: float = 0.0,
) -> CashAffordabilityResult:
    """Paying cash isn't a monthly cashflow question like an installment is —
    it's "do I have the money sitting in savings right now". So this checks
    the balance directly instead of running a month-by-month leftover
    comparison."""
    savings_after = current_savings - price
    affordable = savings_after >= safety_buffer
    shortfall = 0.0 if affordable else safety_buffer - savings_after
    return CashAffordabilityResult(
        savings_before=current_savings,
        savings_after=savings_after,
        affordable=affordable,
        shortfall=shortfall,
    )


def fee_amount(price: float, fee_value: float, fee_is_percent: bool) -> float:
    return round(price * fee_value / 100.0, 2) if fee_is_percent else round(fee_value, 2)


def installment_amount(price: float, down_payment: float, duration_months: int) -> float:
    if duration_months <= 0:
        return 0.0
    return round((price - down_payment) / duration_months, 2)
