"""Tests of the TARGET closing-day calendar (investment spec A5.1, v1.6).

The Good Friday and Easter Monday anchors come from the ECB's own table of
TARGET closing days
(https://www.ecb.europa.eu/ecb/contacts/working-hours/html/index.en.html,
checked 20260925). The most important test is ``TestNotClosed``: ECB staff
holidays are not TARGET closing days — the mistake this module exists to
prevent.
"""

from __future__ import annotations

import datetime as dt

import pytest

from trading_app.target_calendar import easter_sunday, is_target_closing_day

D = dt.date
ONE_DAY = dt.timedelta(days=1)


class TestEaster:
    @pytest.mark.parametrize(
        ("easter", "good_friday", "easter_monday"),
        [
            (D(2026, 4, 5), D(2026, 4, 3), D(2026, 4, 6)),
            (D(2027, 3, 28), D(2027, 3, 26), D(2027, 3, 29)),
            (D(2028, 4, 16), D(2028, 4, 14), D(2028, 4, 17)),
        ],
    )
    def test_ecb_anchors(self, easter, good_friday, easter_monday) -> None:
        assert easter_sunday(easter.year) == easter
        assert is_target_closing_day(good_friday)
        assert is_target_closing_day(easter_monday)
        # The Thursday before and the Tuesday after are business days.
        assert not is_target_closing_day(good_friday - ONE_DAY)
        assert not is_target_closing_day(easter_monday + ONE_DAY)

    @pytest.mark.parametrize(
        "easter",
        [
            D(2000, 4, 23),
            D(2008, 3, 23),
            D(2011, 4, 24),
            D(2019, 4, 21),
            D(2024, 3, 31),
            D(2025, 4, 20),
            D(2038, 4, 25),  # the latest possible date
            D(2285, 3, 22),  # the earliest possible date
        ],
    )
    def test_known_easter_sundays(self, easter) -> None:
        assert easter_sunday(easter.year) == easter

    def test_always_a_sunday_between_22_march_and_25_april(self) -> None:
        for year in range(1583, 4100):
            easter = easter_sunday(year)
            assert easter.weekday() == 6, year
            assert D(year, 3, 22) <= easter <= D(year, 4, 25), year


class TestClosingDays:
    def test_exactly_the_six_holidays_and_weekends(self) -> None:
        """Every day of a century: closed iff weekend or one of the six."""
        for year in range(2000, 2101):
            easter = easter_sunday(year)
            holidays = {
                D(year, 1, 1),
                easter - 2 * ONE_DAY,  # Good Friday
                easter + ONE_DAY,  # Easter Monday
                D(year, 5, 1),
                D(year, 12, 25),
                D(year, 12, 26),
            }
            day = D(year, 1, 1)
            while day.year == year:
                assert is_target_closing_day(day) == (day.weekday() >= 5 or day in holidays), day
                day += ONE_DAY

    @pytest.mark.parametrize(
        "day",
        [D(2026, 1, 1), D(2026, 5, 1), D(2026, 12, 25), D(2025, 12, 26)],
    )
    def test_fixed_holidays_on_a_weekday(self, day) -> None:
        assert day.weekday() < 5
        assert is_target_closing_day(day)

    def test_weekends_are_closed(self) -> None:
        assert is_target_closing_day(D(2026, 8, 29))  # Saturday
        assert is_target_closing_day(D(2026, 8, 30))  # Sunday
        assert not is_target_closing_day(D(2026, 8, 31))  # Monday


class TestNotClosed:
    @pytest.mark.parametrize(
        "day",
        [
            D(2026, 5, 14),  # Ascension Day (Easter + 39)
            D(2026, 5, 25),  # Whit Monday (Easter + 50)
            D(2026, 6, 4),  # Corpus Christi (Easter + 60)
            D(2025, 10, 3),  # Day of German Unity
            D(2027, 11, 1),  # All Saints' Day
            D(2026, 12, 24),  # Christmas Eve
            D(2026, 12, 31),  # New Year's Eve — some third parties wrongly list it
        ],
    )
    def test_ecb_staff_holidays_are_business_days(self, day) -> None:
        assert day.weekday() < 5  # otherwise the test would prove nothing
        assert not is_target_closing_day(day)

    @pytest.mark.parametrize(
        "day",
        [
            D(2027, 12, 27),  # 25 and 26 December 2027 are Saturday and Sunday
            D(2028, 1, 3),  # 1 January 2028 is a Saturday
            D(2027, 5, 3),  # 1 May 2027 is a Saturday
        ],
    )
    def test_no_observed_holiday_after_a_weekend(self, day) -> None:
        assert day.weekday() == 0
        assert not is_target_closing_day(day)
