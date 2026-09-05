"""
Human-readable durations.

Time worked is stored as a decimal number of hours because that is what payroll
arithmetic needs — you cannot multiply "8h 27m" by an overtime rate. But nobody
reads their timesheet in hundredths of an hour. "8.45" is not eight hours and
forty-five minutes; it is eight hours and twenty-seven, and a payslip that
invites that misreading is a payslip that generates support tickets.

So: decimal in the database and the engine, hours and minutes on every screen.
The mockup agrees — its attendance widget reads `6h56`, not `6.93`.
"""

from decimal import Decimal

ZERO = Decimal("0.00")


def hours_minutes(value, *, blank="—") -> str:
    """
    Format decimal hours as `8h 27m`.

    Under an hour drops the hour part (`45m`) so a short session does not read
    as `0h 45m`. Exactly zero returns `blank`, because a dash says "nothing
    here" where `0h 00m` says "we measured, and it was nothing" — usually the
    first is what an empty attendance row means.
    """
    if value is None:
        return blank
    try:
        total = Decimal(str(value))
    except Exception:
        return blank

    negative = total < 0
    total = abs(total)
    minutes = int((total * 60).quantize(Decimal("1")))
    if minutes == 0:
        return blank

    hours, mins = divmod(minutes, 60)
    text = f"{hours}h {mins:02d}m" if hours else f"{mins}m"
    return f"-{text}" if negative else text


def hours_minutes_compact(value) -> str:
    """`6h56`, the form the mockup's attendance widget uses."""
    if value is None:
        return "0h00"
    try:
        total = abs(Decimal(str(value)))
    except Exception:
        return "0h00"
    minutes = int((total * 60).quantize(Decimal("1")))
    hours, mins = divmod(minutes, 60)
    return f"{hours}h{mins:02d}"


def days_display(value, *, unit="day") -> str:
    """`3 days`, `1 day`, `0.5 days` — leave counts, without a trailing `.00`."""
    if value is None:
        return "—"
    try:
        number = Decimal(str(value))
    except Exception:
        return "—"
    whole = number == number.to_integral_value()
    text = f"{int(number)}" if whole else f"{number.normalize()}"
    plural = "" if number == 1 else "s"
    return f"{text} {unit}{plural}"
