"""Schedule engine for time-based message display and sound triggers.

Checks current RTC time against configured schedules and invokes
callbacks for display and audio when a schedule is active.
"""

DAY_INDEX = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


def _parse_time(time_str):
    """Parse 'HH:MM' to (hour, minute) tuple."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def _time_to_minutes(hour, minute):
    """Convert hour:minute to minutes since midnight."""
    return hour * 60 + minute


def is_time_in_range(current_h, current_m, start_str, end_str):
    """Check if current time (h, m) falls within start-end range.

    Handles overnight ranges (e.g., 22:00 - 06:00).
    Both start and end are inclusive.
    """
    start_h, start_m = _parse_time(start_str)
    end_h, end_m = _parse_time(end_str)

    current = _time_to_minutes(current_h, current_m)
    start = _time_to_minutes(start_h, start_m)
    end = _time_to_minutes(end_h, end_m)

    if start <= end:
        return start <= current <= end
    else:
        # Overnight range (e.g., 22:00 - 06:00)
        return current >= start or current <= end


def is_day_match(weekday_index, days_list):
    """Check if weekday_index (0=Mon..6=Sun) matches the days list.

    Args:
        weekday_index: 0-6 (Monday=0, Sunday=6)
        days_list: list of day strings like ["mon", "tue", "fri"]
    """
    if not days_list:
        return True
    for day_name in days_list:
        if DAY_INDEX.get(day_name) == weekday_index:
            return True
    return False


def is_schedule_start(current_h, current_m, start_str):
    """Check if current time exactly matches schedule start time.

    Used to trigger one-time events (e.g., play sound) at the start
    of a schedule period.
    """
    start_h, start_m = _parse_time(start_str)
    return current_h == start_h and current_m == start_m


class Scheduler:

    def __init__(self, system_hal):
        self._system = system_hal
        self._schedules = []
        self._on_schedule_active = None
        self._on_schedule_start = None
        self._on_no_schedule = None
        self._last_active_id = None  # Track which schedule was active last check
        self._timezone_offset = 9

    def set_schedules(self, schedules):
        """Update the schedule list from app config."""
        self._schedules = schedules
        self._last_active_id = None

    def set_timezone_offset(self, offset):
        """Set timezone offset from UTC in hours."""
        self._timezone_offset = offset

    def on_schedule_active(self, callback):
        """Register callback(schedule) when a schedule is currently active."""
        self._on_schedule_active = callback

    def on_schedule_start(self, callback):
        """Register callback(schedule) when a schedule starts (once per period)."""
        self._on_schedule_start = callback

    def on_no_schedule(self, callback):
        """Register callback() when no schedule is active."""
        self._on_no_schedule = callback

    def get_current_time(self):
        """Get current local time as (year, month, day, weekday, hour, minute, second).

        Applies timezone offset to RTC time (which is UTC from NTP).
        MicroPython RTC weekday: 0=Monday..6=Sunday
        """
        rtc = self._system.get_rtc_time()
        # RTC format: (year, month, day, weekday, hour, minute, second, subsecond)
        year, month, day, weekday, hour, minute, second = (
            rtc[0], rtc[1], rtc[2], rtc[3], rtc[4], rtc[5], rtc[6]
        )

        # Apply timezone offset
        hour += self._timezone_offset
        if hour >= 24:
            hour -= 24
            weekday = (weekday + 1) % 7
        elif hour < 0:
            hour += 24
            weekday = (weekday - 1) % 7

        return year, month, day, weekday, hour, minute, second

    def check(self):
        """Check schedules against current time. Call this every minute.

        Invokes registered callbacks as appropriate.
        """
        _, _, _, weekday, hour, minute, _ = self.get_current_time()

        active_found = False
        current_minute_key = hour * 60 + minute

        for sched in self._schedules:
            if not sched.get("enabled", True):
                continue

            if not is_day_match(weekday, sched.get("days", [])):
                continue

            start_time = sched.get("start_time", "00:00")
            end_time = sched.get("end_time", "23:59")

            if is_time_in_range(hour, minute, start_time, end_time):
                active_found = True
                sched_id = sched.get("id", 0)

                if self._on_schedule_active:
                    self._on_schedule_active(sched)

                # Fire on_schedule_start when this schedule was NOT active
                # on the previous check (transition-based, not time-based).
                # This handles: exact start time, mid-schedule save, reboot
                if sched_id != self._last_active_id:
                    if self._on_schedule_start:
                        self._on_schedule_start(sched)

                self._last_active_id = sched_id
                break  # First matching schedule wins

        if not active_found:
            self._last_active_id = None

        if not active_found and self._on_no_schedule:
            self._on_no_schedule()

        return active_found
