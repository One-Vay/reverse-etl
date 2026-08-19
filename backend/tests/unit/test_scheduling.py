"""Unit tests for the hours/days interval scheduling helpers."""

from datetime import datetime, timedelta, timezone

from app.features.syncs.models import IntervalUnit
from app.features.syncs.scheduling import calculate_next_run, project_occurrences


class TestCalculateNextRunHours:
    def test_advances_by_the_interval_in_hours(self):
        anchor = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(3, IntervalUnit.HOURS, None, anchor=anchor)
        assert next_run == anchor + timedelta(hours=3)

    def test_ignores_run_at_time_for_hours(self):
        anchor = datetime(2026, 1, 1, 9, 17, tzinfo=timezone.utc)
        next_run = calculate_next_run(1, IntervalUnit.HOURS, "23:59", anchor=anchor)
        assert next_run == anchor + timedelta(hours=1)


class TestCalculateNextRunDays:
    def test_same_day_if_run_at_time_still_ahead(self):
        anchor = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(1, IntervalUnit.DAYS, "09:00", anchor=anchor)
        assert next_run == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)

    def test_rolls_over_to_the_next_occurrence_if_run_at_time_already_passed(self):
        anchor = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(1, IntervalUnit.DAYS, "09:00", anchor=anchor)
        assert next_run == datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)

    def test_respects_a_multi_day_interval(self):
        anchor = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(3, IntervalUnit.DAYS, "09:00", anchor=anchor)
        assert next_run == datetime(2026, 1, 4, 9, 0, tzinfo=timezone.utc)

    def test_defaults_to_0900_when_run_at_time_is_unset(self):
        anchor = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(1, IntervalUnit.DAYS, None, anchor=anchor)
        assert next_run == datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)

    def test_exactly_at_run_at_time_rolls_to_next_occurrence(self):
        anchor = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        next_run = calculate_next_run(1, IntervalUnit.DAYS, "09:00", anchor=anchor)
        assert next_run == datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)


class TestProjectOccurrences:
    def test_hourly_occurrences_within_the_window(self):
        start = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        occurrences = project_occurrences(
            6, IntervalUnit.HOURS, None, starting_from=start, within=timedelta(days=1)
        )
        assert occurrences == [
            start,
            start + timedelta(hours=6),
            start + timedelta(hours=12),
            start + timedelta(hours=18),
            start + timedelta(hours=24),
        ]

    def test_daily_occurrences_within_a_week(self):
        start = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        occurrences = project_occurrences(
            1,
            IntervalUnit.DAYS,
            "09:00",
            starting_from=start,
            within=timedelta(days=7),
        )
        assert len(occurrences) == 8  # inclusive of day 0 through day 7
        assert occurrences[0] == start
        assert occurrences[-1] == start + timedelta(days=7)

    def test_empty_window_returns_nothing(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert (
            project_occurrences(
                1, IntervalUnit.HOURS, None, starting_from=start, within=timedelta(0)
            )
            == []
        )

    def test_zero_interval_is_bounded_not_infinite(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        occurrences = project_occurrences(
            0, IntervalUnit.HOURS, None, starting_from=start, within=timedelta(days=1)
        )
        assert len(occurrences) <= 1000
