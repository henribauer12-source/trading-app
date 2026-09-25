"""TARGET closing days (investment spec A5.1, v1.6).

The ECB publishes its euro foreign-exchange reference rates on TARGET
business days. On a closing day there is no rate, and carrying the last one
forward is legitimate (A5.1, as in strategy catalogue G4). On a business day
there must be one: a missing rate there is a data gap, not a holiday. This
module tells the two apart; ``InstrumentView.rate_for`` uses it.

Closing days, as marked in the ECB's own table
(https://www.ecb.europa.eu/ecb/contacts/working-hours/html/index.en.html,
checked 20260925) — exactly six, plus Saturdays and Sundays:

- New Year's Day, 1 January
- Good Friday (movable)
- Easter Monday (movable)
- Labour Day, 1 May
- Christmas Day, 25 December
- 26 December

None of them moves when it falls on a weekend; it is simply closed already.
Not closing days, although the ECB's staff have the day off: Ascension Day,
Whit Monday, Corpus Christi, Day of German Unity, All Saints' Day, Christmas
Eve and New Year's Eve. TARGET is open and rates are published. Some third
parties list 31 December as closed; the ECB's table does not.
"""

from __future__ import annotations

import datetime as dt

__all__ = ["easter_sunday", "is_target_closing_day"]

# (month, day) of the four fixed closing days.
_FIXED_CLOSING_DAYS = frozenset({(1, 1), (5, 1), (12, 25), (12, 26)})


def easter_sunday(year: int) -> dt.date:
    """Gregorian (Western) Easter Sunday of ``year``.

    The anonymous Gregorian algorithm as given by Meeus, *Astronomical
    Algorithms*, ch. 8: integer arithmetic only, valid for every Gregorian
    year. Variable names as in Meeus.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741 — Meeus' name
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return dt.date(year, month, day + 1)


def is_target_closing_day(day: dt.date) -> bool:
    """True on a Saturday, a Sunday or one of the six TARGET holidays."""
    if day.weekday() >= 5 or (day.month, day.day) in _FIXED_CLOSING_DAYS:
        return True
    easter = easter_sunday(day.year)
    # Good Friday and Easter Monday.
    return day in (easter - dt.timedelta(days=2), easter + dt.timedelta(days=1))
