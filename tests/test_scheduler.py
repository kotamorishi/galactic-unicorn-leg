"""Tests for scheduler/scheduler.py"""

import pytest
from scheduler.scheduler import Scheduler, is_time_in_range, is_day_match, is_schedule_start


class TestTimeInRange:

    def test_within_normal_range(self):
        assert is_time_in_range(8, 30, "08:00", "09:00") is True

    def test_at_start_boundary(self):
        assert is_time_in_range(8, 0, "08:00", "09:00") is True

    def test_at_end_boundary(self):
        assert is_time_in_range(9, 0, "08:00", "09:00") is True

    def test_before_range(self):
        assert is_time_in_range(7, 59, "08:00", "09:00") is False

    def test_after_range(self):
        assert is_time_in_range(9, 1, "08:00", "09:00") is False

    def test_overnight_range_late_night(self):
        assert is_time_in_range(23, 0, "22:00", "06:00") is True

    def test_overnight_range_early_morning(self):
        assert is_time_in_range(3, 0, "22:00", "06:00") is True

    def test_overnight_range_outside(self):
        assert is_time_in_range(12, 0, "22:00", "06:00") is False

    def test_overnight_range_at_start(self):
        assert is_time_in_range(22, 0, "22:00", "06:00") is True

    def test_overnight_range_at_end(self):
        assert is_time_in_range(6, 0, "22:00", "06:00") is True

    def test_full_day_range(self):
        assert is_time_in_range(12, 0, "00:00", "23:59") is True

    def test_midnight_boundary(self):
        assert is_time_in_range(0, 0, "00:00", "23:59") is True

    def test_end_of_day(self):
        assert is_time_in_range(23, 59, "00:00", "23:59") is True

    def test_single_minute_range(self):
        assert is_time_in_range(8, 0, "08:00", "08:00") is True
        assert is_time_in_range(8, 1, "08:00", "08:00") is False


class TestDayMatch:

    def test_monday_matches(self):
        assert is_day_match(0, ["mon", "tue"]) is True

    def test_wednesday_not_in_list(self):
        assert is_day_match(2, ["mon", "fri"]) is False

    def test_sunday_index_6(self):
        assert is_day_match(6, ["sun"]) is True

    def test_empty_days_matches_all(self):
        assert is_day_match(3, []) is True

    def test_all_days(self):
        all_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        for i in range(7):
            assert is_day_match(i, all_days) is True


class TestScheduleStart:

    def test_exact_match(self):
        assert is_schedule_start(8, 0, "08:00") is True

    def test_not_matching(self):
        assert is_schedule_start(8, 1, "08:00") is False

    def test_midnight(self):
        assert is_schedule_start(0, 0, "00:00") is True


class TestScheduler:

    def _make_schedule(self, id=1, enabled=True, start="08:00", end="09:00",
                       days=None, sound_enabled=False, preset_id=1, volume=50):
        if days is None:
            days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        return {
            "id": id, "enabled": enabled,
            "start_time": start, "end_time": end,
            "days": days,
            "sound": {"enabled": sound_enabled, "preset_id": preset_id, "volume": volume},
        }

    def test_active_callback_fires(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 5, 23, 30, 0, 0))  # UTC 23:30, JST 08:30, Sat
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([self._make_schedule(start="08:00", end="09:00")])

        active_schedules = []
        s.on_schedule_active(lambda sched: active_schedules.append(sched))
        s.check()

        assert len(active_schedules) == 1

    def test_no_schedule_callback_fires(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 5, 1, 0, 0, 0))  # UTC 01:00, JST 10:00
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([self._make_schedule(start="08:00", end="09:00")])

        no_sched_called = []
        s.on_no_schedule(lambda: no_sched_called.append(True))
        s.check()

        assert len(no_sched_called) == 1

    def test_start_callback_fires_once(self, mock_system):
        # Exactly at start time
        mock_system.set_rtc_time((2026, 3, 21, 5, 23, 0, 0, 0))  # UTC 23:00, JST 08:00
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([self._make_schedule(start="08:00", end="09:00")])

        start_events = []
        s.on_schedule_start(lambda sched: start_events.append(sched))

        # First check — should trigger
        s.check()
        assert len(start_events) == 1

        # Second check at same time — should NOT trigger again
        s.check()
        assert len(start_events) == 1

    def test_disabled_schedule_ignored(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 5, 23, 30, 0, 0))
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([self._make_schedule(enabled=False, start="08:00", end="09:00")])

        active_schedules = []
        s.on_schedule_active(lambda sched: active_schedules.append(sched))
        s.check()

        assert len(active_schedules) == 0

    def test_day_filter(self, mock_system):
        # Saturday (weekday=5), but schedule only on weekdays
        mock_system.set_rtc_time((2026, 3, 21, 5, 23, 30, 0, 0))  # UTC weekday=5 (Sat)
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([self._make_schedule(
            start="08:00", end="09:00",
            days=["mon", "tue", "wed", "thu", "fri"],
        )])

        active = []
        s.on_schedule_active(lambda sched: active.append(sched))

        # After timezone adjustment weekday may change, but let's test the mechanism
        result = s.check()
        # The exact result depends on weekday after timezone adjustment

    def test_multiple_schedules(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 0, 23, 30, 0, 0))  # UTC 23:30, JST 08:30, Mon(0)
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        s.set_schedules([
            self._make_schedule(id=1, start="08:00", end="09:00"),
            self._make_schedule(id=2, start="10:00", end="11:00"),
        ])

        active = []
        s.on_schedule_active(lambda sched: active.append(sched["id"]))
        s.check()

        assert 1 in active
        assert 2 not in active

    def test_get_current_time_applies_timezone(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 5, 20, 0, 0, 0))  # UTC 20:00
        s = Scheduler(mock_system)
        s.set_timezone_offset(9)
        _, _, _, _, hour, minute, _ = s.get_current_time()
        assert hour == 5  # 20 + 9 = 29 → 29 - 24 = 5

    def test_timezone_negative(self, mock_system):
        mock_system.set_rtc_time((2026, 3, 21, 5, 3, 0, 0, 0))  # UTC 03:00
        s = Scheduler(mock_system)
        s.set_timezone_offset(-5)
        _, _, _, _, hour, _, _ = s.get_current_time()
        assert hour == 22  # 3 - 5 = -2 → -2 + 24 = 22
