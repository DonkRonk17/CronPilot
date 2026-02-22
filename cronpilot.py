#!/usr/bin/env python3
"""
CronPilot - Cron Expression Parser, Builder & Scheduler

Parse, validate, explain, and schedule cron expressions with zero dependencies.
Every developer struggles with cron syntax - CronPilot makes it intuitive.

Supports standard 5-field cron (minute hour day month weekday) and common
extensions. Provides both a full-featured CLI and a clean Python API.

Author: ATLAS (Team Brain)
For: Logan Smith / Metaphy LLC
Version: 1.0
Date: February 22, 2026
License: MIT
"""

import argparse
import calendar
import datetime
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


__version__ = "1.0.0"
__author__ = "ATLAS (Team Brain)"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIELD_NAMES = ("minute", "hour", "day", "month", "weekday")

FIELD_RANGES: Dict[str, Tuple[int, int]] = {
    "minute":  (0, 59),
    "hour":    (0, 23),
    "day":     (1, 31),
    "month":   (1, 12),
    "weekday": (0, 6),   # 0=Sunday in traditional cron; we normalise below
}

MONTH_NAMES = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

WEEKDAY_NAMES = {
    "sun": 0, "mon": 1, "tue": 2, "wed": 3,
    "thu": 4, "fri": 5, "sat": 6,
}

ORDINAL_SUFFIXES = {1: "st", 2: "nd", 3: "rd"}

PRESETS: Dict[str, Dict[str, str]] = {
    "every_minute":     {"expression": "* * * * *",      "description": "Every minute"},
    "every_5_minutes":  {"expression": "*/5 * * * *",    "description": "Every 5 minutes"},
    "every_15_minutes": {"expression": "*/15 * * * *",   "description": "Every 15 minutes"},
    "every_30_minutes": {"expression": "*/30 * * * *",   "description": "Every 30 minutes"},
    "hourly":           {"expression": "0 * * * *",      "description": "Every hour at minute 0"},
    "daily":            {"expression": "0 0 * * *",      "description": "Every day at midnight"},
    "daily_9am":        {"expression": "0 9 * * *",      "description": "Every day at 9:00 AM"},
    "daily_noon":       {"expression": "0 12 * * *",     "description": "Every day at noon"},
    "daily_6pm":        {"expression": "0 18 * * *",     "description": "Every day at 6:00 PM"},
    "weekly":           {"expression": "0 0 * * 0",      "description": "Every Sunday at midnight"},
    "weekdays":         {"expression": "0 9 * * 1-5",    "description": "Weekdays at 9:00 AM"},
    "weekends":         {"expression": "0 10 * * 0,6",   "description": "Weekends at 10:00 AM"},
    "monthly":          {"expression": "0 0 1 * *",      "description": "First day of every month at midnight"},
    "quarterly":        {"expression": "0 0 1 1,4,7,10 *", "description": "First day of each quarter at midnight"},
    "yearly":           {"expression": "0 0 1 1 *",      "description": "January 1st at midnight"},
    "twice_daily":      {"expression": "0 8,20 * * *",   "description": "Every day at 8:00 AM and 8:00 PM"},
    "every_2_hours":    {"expression": "0 */2 * * *",    "description": "Every 2 hours at minute 0"},
    "business_hours":   {"expression": "0 9-17 * * 1-5", "description": "Every hour 9 AM - 5 PM on weekdays"},
    "end_of_month":     {"expression": "0 0 28-31 * *",  "description": "Last days of month at midnight (28-31)"},
    "reboot":           {"expression": "@reboot",        "description": "Run once at startup"},
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CronError(Exception):
    """Base exception for CronPilot errors."""


class CronParseError(CronError):
    """Raised when a cron expression cannot be parsed."""


class CronValidationError(CronError):
    """Raised when a cron field value is out of range."""


class CronBuildError(CronError):
    """Raised when a cron expression cannot be built from parameters."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ordinal(n: int) -> str:
    """Return ordinal string for an integer (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{ORDINAL_SUFFIXES.get(n % 10, 'th')}"


def _format_time_12h(hour: int, minute: int) -> str:
    """Format hour:minute as 12-hour time string."""
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    if minute == 0:
        return f"{display_hour}:00 {period}"
    return f"{display_hour}:{minute:02d} {period}"


def _weekday_name(day_num: int) -> str:
    """Convert weekday number (0=Sun) to name."""
    names = ["Sunday", "Monday", "Tuesday", "Wednesday",
             "Thursday", "Friday", "Saturday"]
    return names[day_num % 7]


def _month_name(month_num: int) -> str:
    """Convert month number (1-12) to name."""
    return calendar.month_name[month_num]


def _resolve_name(token: str, names_map: Dict[str, int]) -> str:
    """Replace 3-letter name abbreviations with their numeric equivalents."""
    lower = token.lower()
    if lower in names_map:
        return str(names_map[lower])
    return token


def _python_weekday_to_cron(py_wd: int) -> int:
    """Convert Python weekday (0=Monday) to cron weekday (0=Sunday)."""
    return (py_wd + 1) % 7


def _cron_weekday_to_python(cron_wd: int) -> int:
    """Convert cron weekday (0=Sunday) to Python weekday (0=Monday)."""
    return (cron_wd - 1) % 7


# ---------------------------------------------------------------------------
# Field Parser
# ---------------------------------------------------------------------------

def _parse_field(raw: str, field_name: str) -> List[int]:
    """
    Parse a single cron field into a sorted list of integer values.

    Supports: *, */N, N, N-M, N-M/S, N,M,O and name aliases.
    """
    lo, hi = FIELD_RANGES[field_name]
    names_map: Dict[str, int] = {}
    if field_name == "month":
        names_map = MONTH_NAMES
    elif field_name == "weekday":
        names_map = WEEKDAY_NAMES

    raw = raw.strip()
    if not raw:
        raise CronParseError(f"Empty {field_name} field")

    result: set = set()

    for part in raw.split(","):
        part = part.strip()
        if not part:
            raise CronParseError(f"Empty sub-expression in {field_name} field")

        step = None
        if "/" in part:
            base, step_str = part.split("/", 1)
            step_str = _resolve_name(step_str, names_map)
            try:
                step = int(step_str)
            except ValueError:
                raise CronParseError(
                    f"Invalid step '{step_str}' in {field_name} field"
                )
            if step <= 0:
                raise CronValidationError(
                    f"Step must be positive in {field_name} field, got {step}"
                )
            part = base.strip()

        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            range_parts = part.split("-", 1)
            range_parts = [_resolve_name(r.strip(), names_map) for r in range_parts]
            try:
                start = int(range_parts[0])
                end = int(range_parts[1])
            except ValueError:
                raise CronParseError(
                    f"Invalid range '{part}' in {field_name} field"
                )
        else:
            part = _resolve_name(part, names_map)
            try:
                val = int(part)
            except ValueError:
                raise CronParseError(
                    f"Invalid value '{part}' in {field_name} field"
                )
            if step is not None:
                start, end = val, hi
            else:
                if val < lo or val > hi:
                    raise CronValidationError(
                        f"{field_name} value {val} out of range "
                        f"({lo}-{hi})"
                    )
                result.add(val)
                continue

        if start < lo or start > hi:
            raise CronValidationError(
                f"{field_name} start value {start} out of range ({lo}-{hi})"
            )
        if end < lo or end > hi:
            raise CronValidationError(
                f"{field_name} end value {end} out of range ({lo}-{hi})"
            )

        if step is None:
            step = 1

        if start <= end:
            current = start
            while current <= end:
                result.add(current)
                current += step
        else:
            # Wrap-around range (e.g., weekday 5-1 means Fri-Mon)
            current = start
            while current <= hi:
                result.add(current)
                current += step
            current = lo
            while current <= end:
                result.add(current)
                current += step

    return sorted(result)


# ---------------------------------------------------------------------------
# CronExpression
# ---------------------------------------------------------------------------

class CronExpression:
    """
    Represents a parsed cron expression.

    Standard 5-field format: minute hour day month weekday

    Args:
        expression: A cron expression string (e.g. "0 9 * * 1-5").

    Raises:
        CronParseError: If the expression is malformed.
        CronValidationError: If field values are out of range.

    Example:
        >>> cron = CronExpression("*/15 9-17 * * 1-5")
        >>> cron.explain()
        'Every 15 minutes, 9:00 AM through 5:00 PM, Monday through Friday'
    """

    SPECIAL_EXPRESSIONS = {
        "@yearly":   "0 0 1 1 *",
        "@annually": "0 0 1 1 *",
        "@monthly":  "0 0 1 * *",
        "@weekly":   "0 0 * * 0",
        "@daily":    "0 0 * * *",
        "@midnight": "0 0 * * *",
        "@hourly":   "0 * * * *",
    }

    def __init__(self, expression: str):
        if not expression or not isinstance(expression, str):
            raise CronParseError("Expression must be a non-empty string")

        self.original = expression.strip()

        # Handle special @-expressions (except @reboot which has no schedule)
        resolved = self.original
        if resolved.lower() in self.SPECIAL_EXPRESSIONS:
            resolved = self.SPECIAL_EXPRESSIONS[resolved.lower()]
        elif resolved.lower() == "@reboot":
            raise CronParseError(
                "@reboot is a special directive, not a schedulable expression"
            )

        fields = resolved.split()
        if len(fields) != 5:
            raise CronParseError(
                f"Expected 5 fields (minute hour day month weekday), "
                f"got {len(fields)}: '{self.original}'"
            )

        self.raw_fields = fields
        self.minutes = _parse_field(fields[0], "minute")
        self.hours = _parse_field(fields[1], "hour")
        self.days = _parse_field(fields[2], "day")
        self.months = _parse_field(fields[3], "month")
        self.weekdays = _parse_field(fields[4], "weekday")

    def __repr__(self) -> str:
        return f"CronExpression('{self.original}')"

    def __str__(self) -> str:
        return self.original

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CronExpression):
            return NotImplemented
        return (self.minutes == other.minutes and
                self.hours == other.hours and
                self.days == other.days and
                self.months == other.months and
                self.weekdays == other.weekdays)

    @property
    def is_wildcard_day(self) -> bool:
        """True if both day-of-month and weekday are unrestricted."""
        all_days = list(range(1, 32))
        all_weekdays = list(range(0, 7))
        return self.days == all_days and self.weekdays == all_weekdays

    def matches(self, dt: datetime.datetime) -> bool:
        """
        Check whether a datetime matches this cron expression.

        Args:
            dt: The datetime to check.

        Returns:
            True if the datetime would trigger this cron.

        Example:
            >>> cron = CronExpression("0 9 * * 1-5")
            >>> import datetime
            >>> # Monday at 9:00 AM
            >>> cron.matches(datetime.datetime(2026, 2, 23, 9, 0))
            True
        """
        if not isinstance(dt, datetime.datetime):
            raise TypeError(f"Expected datetime, got {type(dt).__name__}")

        if dt.minute not in self.minutes:
            return False
        if dt.hour not in self.hours:
            return False
        if dt.month not in self.months:
            return False

        cron_wd = _python_weekday_to_cron(dt.weekday())

        all_days = list(range(1, 32))
        all_weekdays = list(range(0, 7))
        day_restricted = self.days != all_days
        weekday_restricted = self.weekdays != all_weekdays

        if day_restricted and weekday_restricted:
            # Standard cron: day OR weekday (union)
            return dt.day in self.days or cron_wd in self.weekdays
        elif day_restricted:
            return dt.day in self.days
        elif weekday_restricted:
            return cron_wd in self.weekdays
        else:
            return True

    def next_runs(
        self,
        count: int = 5,
        after: Optional[datetime.datetime] = None
    ) -> List[datetime.datetime]:
        """
        Calculate the next N datetimes that match this cron.

        Args:
            count: Number of matching times to return (default 5).
            after: Start searching after this time (default: now).

        Returns:
            List of datetime objects for the next matching times.

        Example:
            >>> cron = CronExpression("0 0 * * *")
            >>> runs = cron.next_runs(3)
            >>> len(runs)
            3
        """
        if count <= 0:
            raise ValueError("count must be positive")
        if count > 1000:
            raise ValueError("count cannot exceed 1000")

        if after is None:
            after = datetime.datetime.now()

        results: List[datetime.datetime] = []
        # Start at the next minute boundary
        dt = after.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        max_iterations = 525960  # ~1 year of minutes

        for _ in range(max_iterations):
            if self.matches(dt):
                results.append(dt)
                if len(results) >= count:
                    break
            dt += datetime.timedelta(minutes=1)
        return results

    def previous_runs(
        self,
        count: int = 5,
        before: Optional[datetime.datetime] = None
    ) -> List[datetime.datetime]:
        """
        Calculate the previous N datetimes that matched this cron.

        Args:
            count: Number of matching times to return (default 5).
            before: Start searching before this time (default: now).

        Returns:
            List of datetime objects for the previous matching times
            (most recent first).
        """
        if count <= 0:
            raise ValueError("count must be positive")
        if count > 1000:
            raise ValueError("count cannot exceed 1000")

        if before is None:
            before = datetime.datetime.now()

        results: List[datetime.datetime] = []
        dt = before.replace(second=0, microsecond=0) - datetime.timedelta(minutes=1)
        max_iterations = 525960

        for _ in range(max_iterations):
            if self.matches(dt):
                results.append(dt)
                if len(results) >= count:
                    break
            dt -= datetime.timedelta(minutes=1)
        return results

    def explain(self) -> str:
        """
        Generate a human-readable English explanation of this cron.

        Returns:
            Plain English description of the schedule.

        Example:
            >>> CronExpression("0 9 * * 1-5").explain()
            'At 9:00 AM, Monday through Friday'
        """
        parts: List[str] = []

        # Minute description
        min_desc = self._describe_minute()
        if min_desc:
            parts.append(min_desc)

        # Hour description
        hour_desc = self._describe_hour()
        if hour_desc:
            parts.append(hour_desc)

        # Day-of-month description
        day_desc = self._describe_day()
        if day_desc:
            parts.append(day_desc)

        # Month description
        month_desc = self._describe_month()
        if month_desc:
            parts.append(month_desc)

        # Weekday description
        wd_desc = self._describe_weekday()
        if wd_desc:
            parts.append(wd_desc)

        return ", ".join(parts) if parts else "Every minute"

    def _describe_minute(self) -> str:
        all_mins = list(range(0, 60))
        if self.minutes == all_mins:
            return "Every minute"
        if len(self.minutes) == 1:
            val = self.minutes[0]
            if self.hours == list(range(0, 24)):
                return f"At minute {val} of every hour"
            return ""  # minute info folded into hour desc
        # Check for step pattern
        step = self._detect_step(self.minutes, 0, 59)
        if step:
            return f"Every {step} minutes"
        if len(self.minutes) <= 5:
            return "At minutes " + ", ".join(str(m) for m in self.minutes)
        return f"At {len(self.minutes)} specific minutes"

    def _describe_hour(self) -> str:
        all_hours = list(range(0, 24))
        if self.hours == all_hours:
            return ""
        if len(self.hours) == 1:
            h = self.hours[0]
            if len(self.minutes) == 1:
                return f"At {_format_time_12h(h, self.minutes[0])}"
            return f"During the {_format_time_12h(h, 0).split(':')[0]} hour"
        # Check for range
        if self._is_contiguous(self.hours):
            return (f"{_format_time_12h(self.hours[0], 0)} through "
                    f"{_format_time_12h(self.hours[-1], 0)}")
        step = self._detect_step(self.hours, 0, 23)
        if step:
            return f"Every {step} hours"
        times = [_format_time_12h(h, 0) for h in self.hours]
        return "At " + " and ".join(times)

    def _describe_day(self) -> str:
        all_days = list(range(1, 32))
        if self.days == all_days:
            return ""
        if len(self.days) == 1:
            return f"On the {_ordinal(self.days[0])}"
        if self._is_contiguous(self.days):
            return f"On days {self.days[0]}-{self.days[-1]}"
        return "On days " + ", ".join(str(d) for d in self.days)

    def _describe_month(self) -> str:
        all_months = list(range(1, 13))
        if self.months == all_months:
            return ""
        if len(self.months) == 1:
            return f"In {_month_name(self.months[0])}"
        names = [_month_name(m) for m in self.months]
        if self._is_contiguous(self.months):
            return f"{names[0]} through {names[-1]}"
        return "In " + ", ".join(names)

    def _describe_weekday(self) -> str:
        all_wd = list(range(0, 7))
        if self.weekdays == all_wd:
            return ""
        if len(self.weekdays) == 1:
            return f"On {_weekday_name(self.weekdays[0])}"
        if self.weekdays == [1, 2, 3, 4, 5]:
            return "Monday through Friday"
        if self.weekdays == [0, 6]:
            return "On weekends"
        if self._is_contiguous(self.weekdays):
            return (f"{_weekday_name(self.weekdays[0])} through "
                    f"{_weekday_name(self.weekdays[-1])}")
        names = [_weekday_name(w) for w in self.weekdays]
        return "On " + ", ".join(names)

    @staticmethod
    def _detect_step(values: List[int], lo: int, hi: int) -> Optional[int]:
        """Detect if values form a regular step pattern from lo."""
        if len(values) < 2:
            return None
        step = values[1] - values[0]
        if step <= 1:
            return None
        expected = list(range(lo, hi + 1, step))
        if values == expected:
            return step
        return None

    @staticmethod
    def _is_contiguous(values: List[int]) -> bool:
        """Check if values form a contiguous range."""
        if len(values) < 2:
            return False
        return values == list(range(values[0], values[-1] + 1))

    def to_dict(self) -> Dict:
        """Serialize the cron expression to a dictionary."""
        return {
            "expression": self.original,
            "minutes": self.minutes,
            "hours": self.hours,
            "days": self.days,
            "months": self.months,
            "weekdays": self.weekdays,
            "explanation": self.explain(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize the cron expression to JSON."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# CronBuilder
# ---------------------------------------------------------------------------

class CronBuilder:
    """
    Build cron expressions from human-readable parameters.

    Example:
        >>> builder = CronBuilder()
        >>> builder.every_n_minutes(15).on_weekdays().at_hours(9, 17)
        >>> print(builder.build())
        '*/15 9,17 * * 1-5'
    """

    def __init__(self):
        self._minute = "*"
        self._hour = "*"
        self._day = "*"
        self._month = "*"
        self._weekday = "*"

    def at_minute(self, *minutes: int) -> "CronBuilder":
        """Set specific minute(s)."""
        for m in minutes:
            if m < 0 or m > 59:
                raise CronBuildError(f"Minute {m} out of range (0-59)")
        self._minute = ",".join(str(m) for m in minutes)
        return self

    def every_n_minutes(self, n: int) -> "CronBuilder":
        """Run every N minutes."""
        if n <= 0 or n > 59:
            raise CronBuildError(f"Step {n} out of range (1-59)")
        self._minute = f"*/{n}"
        return self

    def at_hours(self, *hours: int) -> "CronBuilder":
        """Set specific hour(s)."""
        for h in hours:
            if h < 0 or h > 23:
                raise CronBuildError(f"Hour {h} out of range (0-23)")
        self._hour = ",".join(str(h) for h in hours)
        return self

    def every_n_hours(self, n: int) -> "CronBuilder":
        """Run every N hours."""
        if n <= 0 or n > 23:
            raise CronBuildError(f"Step {n} out of range (1-23)")
        self._hour = f"*/{n}"
        return self

    def hour_range(self, start: int, end: int) -> "CronBuilder":
        """Set an hour range (e.g., 9-17 for business hours)."""
        if start < 0 or start > 23 or end < 0 or end > 23:
            raise CronBuildError("Hour range values must be 0-23")
        self._hour = f"{start}-{end}"
        return self

    def on_days(self, *days: int) -> "CronBuilder":
        """Set specific day(s) of month."""
        for d in days:
            if d < 1 or d > 31:
                raise CronBuildError(f"Day {d} out of range (1-31)")
        self._day = ",".join(str(d) for d in days)
        return self

    def in_months(self, *months: int) -> "CronBuilder":
        """Set specific month(s)."""
        for m in months:
            if m < 1 or m > 12:
                raise CronBuildError(f"Month {m} out of range (1-12)")
        self._month = ",".join(str(m) for m in months)
        return self

    def on_weekdays(self) -> "CronBuilder":
        """Run on weekdays only (Mon-Fri)."""
        self._weekday = "1-5"
        return self

    def on_weekends(self) -> "CronBuilder":
        """Run on weekends only (Sat-Sun)."""
        self._weekday = "0,6"
        return self

    def on_specific_weekdays(self, *weekdays: int) -> "CronBuilder":
        """Set specific weekday(s) (0=Sun, 1=Mon, ..., 6=Sat)."""
        for w in weekdays:
            if w < 0 or w > 6:
                raise CronBuildError(f"Weekday {w} out of range (0-6)")
        self._weekday = ",".join(str(w) for w in weekdays)
        return self

    def build(self) -> str:
        """
        Build and return the cron expression string.

        Returns:
            A valid 5-field cron expression.

        Raises:
            CronBuildError: If the resulting expression is invalid.
        """
        expr = f"{self._minute} {self._hour} {self._day} {self._month} {self._weekday}"
        # Validate by parsing
        try:
            CronExpression(expr)
        except CronError as e:
            raise CronBuildError(f"Built expression is invalid: {e}")
        return expr

    def build_explained(self) -> Tuple[str, str]:
        """
        Build and return both the expression and its explanation.

        Returns:
            Tuple of (expression, explanation).
        """
        expr = self.build()
        cron = CronExpression(expr)
        return expr, cron.explain()

    def reset(self) -> "CronBuilder":
        """Reset all fields to wildcard."""
        self._minute = "*"
        self._hour = "*"
        self._day = "*"
        self._month = "*"
        self._weekday = "*"
        return self


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(expression: str) -> Dict[str, Union[bool, str, None]]:
    """
    Validate a cron expression and return detailed results.

    Args:
        expression: The cron expression to validate.

    Returns:
        Dict with keys: valid (bool), expression (str), error (str or None),
        explanation (str or None), fields (dict or None).

    Example:
        >>> result = validate("0 9 * * 1-5")
        >>> result["valid"]
        True
    """
    result: Dict[str, Union[bool, str, None, Dict]] = {
        "valid": False,
        "expression": expression,
        "error": None,
        "explanation": None,
        "fields": None,
    }
    try:
        cron = CronExpression(expression)
        result["valid"] = True
        result["explanation"] = cron.explain()
        result["fields"] = {
            "minute": cron.raw_fields[0] if len(cron.raw_fields) == 5 else None,
            "hour": cron.raw_fields[1] if len(cron.raw_fields) == 5 else None,
            "day": cron.raw_fields[2] if len(cron.raw_fields) == 5 else None,
            "month": cron.raw_fields[3] if len(cron.raw_fields) == 5 else None,
            "weekday": cron.raw_fields[4] if len(cron.raw_fields) == 5 else None,
        }
    except CronError as e:
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# Preset lookup
# ---------------------------------------------------------------------------

def get_preset(name: str) -> Optional[Dict[str, str]]:
    """
    Look up a named preset cron expression.

    Args:
        name: Preset name (e.g., "daily", "weekdays", "hourly").

    Returns:
        Dict with 'expression' and 'description', or None if not found.
    """
    return PRESETS.get(name.lower().replace(" ", "_").replace("-", "_"))


def list_presets() -> Dict[str, Dict[str, str]]:
    """Return all available preset cron expressions."""
    return dict(PRESETS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_explain(args: argparse.Namespace) -> int:
    """Handle 'explain' subcommand."""
    try:
        cron = CronExpression(args.expression)
    except CronError as e:
        print(f"[X] Error: {e}")
        return 1

    if args.json:
        print(cron.to_json())
    else:
        print(f"Expression: {cron.original}")
        print(f"Meaning:    {cron.explain()}")
        print()
        print("Parsed fields:")
        print(f"  Minute:  {cron.raw_fields[0]:10s} -> {cron.minutes}")
        print(f"  Hour:    {cron.raw_fields[1]:10s} -> {cron.hours}")
        print(f"  Day:     {cron.raw_fields[2]:10s} -> {cron.days}")
        print(f"  Month:   {cron.raw_fields[3]:10s} -> {cron.months}")
        print(f"  Weekday: {cron.raw_fields[4]:10s} -> {cron.weekdays}")
    return 0


def _cli_next(args: argparse.Namespace) -> int:
    """Handle 'next' subcommand."""
    try:
        cron = CronExpression(args.expression)
    except CronError as e:
        print(f"[X] Error: {e}")
        return 1

    after = None
    if args.after:
        try:
            after = datetime.datetime.fromisoformat(args.after)
        except ValueError:
            print(f"[X] Invalid datetime: {args.after}")
            print("[!] Use ISO format: YYYY-MM-DDTHH:MM:SS")
            return 1

    runs = cron.next_runs(count=args.count, after=after)

    if args.json:
        data = {
            "expression": cron.original,
            "explanation": cron.explain(),
            "next_runs": [r.isoformat() for r in runs],
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Expression: {cron.original}")
        print(f"Meaning:    {cron.explain()}")
        print(f"\nNext {len(runs)} runs:")
        for i, run in enumerate(runs, 1):
            day_name = calendar.day_name[run.weekday()]
            print(f"  {i:2d}. {run.strftime('%Y-%m-%d %H:%M')}  ({day_name})")
    return 0


def _cli_previous(args: argparse.Namespace) -> int:
    """Handle 'previous' subcommand."""
    try:
        cron = CronExpression(args.expression)
    except CronError as e:
        print(f"[X] Error: {e}")
        return 1

    before = None
    if args.before:
        try:
            before = datetime.datetime.fromisoformat(args.before)
        except ValueError:
            print(f"[X] Invalid datetime: {args.before}")
            return 1

    runs = cron.previous_runs(count=args.count, before=before)

    if args.json:
        data = {
            "expression": cron.original,
            "explanation": cron.explain(),
            "previous_runs": [r.isoformat() for r in runs],
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Expression: {cron.original}")
        print(f"Meaning:    {cron.explain()}")
        print(f"\nPrevious {len(runs)} runs:")
        for i, run in enumerate(runs, 1):
            day_name = calendar.day_name[run.weekday()]
            print(f"  {i:2d}. {run.strftime('%Y-%m-%d %H:%M')}  ({day_name})")
    return 0


def _cli_validate(args: argparse.Namespace) -> int:
    """Handle 'validate' subcommand."""
    result = validate(args.expression)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["valid"]:
            print(f"[OK] Valid cron expression: {args.expression}")
            print(f"     Meaning: {result['explanation']}")
        else:
            print(f"[X] Invalid: {result['error']}")
    return 0 if result["valid"] else 1


def _cli_test(args: argparse.Namespace) -> int:
    """Handle 'test' subcommand."""
    try:
        cron = CronExpression(args.expression)
    except CronError as e:
        print(f"[X] Error: {e}")
        return 1

    try:
        dt = datetime.datetime.fromisoformat(args.datetime)
    except ValueError:
        print(f"[X] Invalid datetime: {args.datetime}")
        print("[!] Use ISO format: YYYY-MM-DDTHH:MM:SS")
        return 1

    match = cron.matches(dt)

    if args.json:
        data = {
            "expression": cron.original,
            "datetime": dt.isoformat(),
            "matches": match,
            "explanation": cron.explain(),
        }
        print(json.dumps(data, indent=2))
    else:
        day_name = calendar.day_name[dt.weekday()]
        if match:
            print(f"[OK] MATCH: {dt.strftime('%Y-%m-%d %H:%M')} ({day_name})")
            print(f"     matches '{cron.original}'")
        else:
            print(f"[X] NO MATCH: {dt.strftime('%Y-%m-%d %H:%M')} ({day_name})")
            print(f"    does not match '{cron.original}'")
        print(f"    Cron meaning: {cron.explain()}")
    return 0


def _cli_build(args: argparse.Namespace) -> int:
    """Handle 'build' subcommand."""
    builder = CronBuilder()

    try:
        if args.minute is not None:
            if args.minute.startswith("*/"):
                builder.every_n_minutes(int(args.minute[2:]))
            else:
                vals = [int(x) for x in args.minute.split(",")]
                builder.at_minute(*vals)

        if args.hour is not None:
            if args.hour.startswith("*/"):
                builder.every_n_hours(int(args.hour[2:]))
            elif "-" in args.hour:
                parts = args.hour.split("-")
                builder.hour_range(int(parts[0]), int(parts[1]))
            else:
                vals = [int(x) for x in args.hour.split(",")]
                builder.at_hours(*vals)

        if args.day is not None:
            vals = [int(x) for x in args.day.split(",")]
            builder.on_days(*vals)

        if args.month is not None:
            vals = [int(x) for x in args.month.split(",")]
            builder.in_months(*vals)

        if args.weekday is not None:
            if args.weekday.lower() == "weekdays":
                builder.on_weekdays()
            elif args.weekday.lower() == "weekends":
                builder.on_weekends()
            else:
                vals = [int(x) for x in args.weekday.split(",")]
                builder.on_specific_weekdays(*vals)

        expr = builder.build()
        cron = CronExpression(expr)

    except (CronError, ValueError) as e:
        print(f"[X] Build error: {e}")
        return 1

    if args.json:
        data = {
            "expression": expr,
            "explanation": cron.explain(),
        }
        print(json.dumps(data, indent=2))
    else:
        print(f"Expression: {expr}")
        print(f"Meaning:    {cron.explain()}")
    return 0


def _cli_presets(args: argparse.Namespace) -> int:
    """Handle 'presets' subcommand."""
    if args.name:
        preset = get_preset(args.name)
        if not preset:
            print(f"[X] Unknown preset: {args.name}")
            print("[!] Use 'cronpilot presets' to list all presets")
            return 1

        if args.json:
            print(json.dumps(preset, indent=2))
        else:
            print(f"Preset:     {args.name}")
            print(f"Expression: {preset['expression']}")
            print(f"Meaning:    {preset['description']}")
            if preset["expression"] != "@reboot":
                cron = CronExpression(preset["expression"])
                runs = cron.next_runs(3)
                print(f"\nNext 3 runs:")
                for i, run in enumerate(runs, 1):
                    day_name = calendar.day_name[run.weekday()]
                    print(f"  {i}. {run.strftime('%Y-%m-%d %H:%M')}  ({day_name})")
        return 0

    # List all presets
    if args.json:
        print(json.dumps(PRESETS, indent=2))
    else:
        print("Available Cron Presets:")
        print("-" * 70)
        max_name = max(len(n) for n in PRESETS)
        max_expr = max(len(p["expression"]) for p in PRESETS.values())
        for name, info in PRESETS.items():
            print(f"  {name:<{max_name}}  {info['expression']:<{max_expr}}  {info['description']}")
        print("-" * 70)
        print(f"Total: {len(PRESETS)} presets")
        print("\nUsage: cronpilot presets <name> for details")
    return 0


def _cli_diff(args: argparse.Namespace) -> int:
    """Handle 'diff' subcommand - compare two cron expressions."""
    try:
        cron1 = CronExpression(args.expression1)
        cron2 = CronExpression(args.expression2)
    except CronError as e:
        print(f"[X] Error: {e}")
        return 1

    equivalent = cron1 == cron2

    if args.json:
        data = {
            "expression1": {"expression": cron1.original, "explanation": cron1.explain()},
            "expression2": {"expression": cron2.original, "explanation": cron2.explain()},
            "equivalent": equivalent,
            "differences": {},
        }
        for field in FIELD_NAMES:
            v1 = getattr(cron1, field + "s" if field != "weekday" else "weekdays")
            v2 = getattr(cron2, field + "s" if field != "weekday" else "weekdays")
            if field == "day":
                v1, v2 = cron1.days, cron2.days
            if v1 != v2:
                data["differences"][field] = {"expr1": v1, "expr2": v2}
        print(json.dumps(data, indent=2))
    else:
        print(f"Expression 1: {cron1.original}")
        print(f"  Meaning:    {cron1.explain()}")
        print(f"Expression 2: {cron2.original}")
        print(f"  Meaning:    {cron2.explain()}")
        print()
        if equivalent:
            print("[OK] These expressions are functionally EQUIVALENT")
        else:
            print("[!] These expressions are DIFFERENT")
            print("\nField differences:")
            field_attrs = [
                ("minute", "minutes"), ("hour", "hours"), ("day", "days"),
                ("month", "months"), ("weekday", "weekdays"),
            ]
            for name, attr in field_attrs:
                v1 = getattr(cron1, attr)
                v2 = getattr(cron2, attr)
                if v1 != v2:
                    print(f"  {name:>8s}: {cron1.raw_fields[FIELD_NAMES.index(name)]:>10s} vs {cron2.raw_fields[FIELD_NAMES.index(name)]:<10s}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point."""
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    parser = argparse.ArgumentParser(
        prog="cronpilot",
        description="CronPilot - Cron Expression Parser, Builder & Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cronpilot explain "0 9 * * 1-5"       Explain a cron expression
  cronpilot next "*/15 * * * *"          Show next 5 run times
  cronpilot next "0 0 * * *" -n 10      Show next 10 runs
  cronpilot validate "0 9 * * 1-5"      Validate syntax
  cronpilot test "0 9 * * 1-5" 2026-02-23T09:00:00
  cronpilot build --minute 0 --hour 9 --weekday weekdays
  cronpilot presets                      List all presets
  cronpilot presets daily_9am            Show preset details
  cronpilot diff "0 9 * * *" "0 9 * * 0-6"

For more info: https://github.com/DonkRonk17/CronPilot
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # --- explain ---
    p_explain = subparsers.add_parser(
        "explain", help="Explain a cron expression in plain English"
    )
    p_explain.add_argument("expression", help="Cron expression (quote it!)")
    p_explain.add_argument("--json", action="store_true", help="Output as JSON")

    # --- next ---
    p_next = subparsers.add_parser("next", help="Show next N run times")
    p_next.add_argument("expression", help="Cron expression")
    p_next.add_argument(
        "-n", "--count", type=int, default=5, help="Number of runs (default: 5)"
    )
    p_next.add_argument(
        "--after", help="Start after this datetime (ISO format)"
    )
    p_next.add_argument("--json", action="store_true", help="Output as JSON")

    # --- previous ---
    p_prev = subparsers.add_parser("previous", help="Show previous N run times")
    p_prev.add_argument("expression", help="Cron expression")
    p_prev.add_argument(
        "-n", "--count", type=int, default=5, help="Number of runs (default: 5)"
    )
    p_prev.add_argument(
        "--before", help="Start before this datetime (ISO format)"
    )
    p_prev.add_argument("--json", action="store_true", help="Output as JSON")

    # --- validate ---
    p_validate = subparsers.add_parser("validate", help="Validate cron syntax")
    p_validate.add_argument("expression", help="Cron expression")
    p_validate.add_argument("--json", action="store_true", help="Output as JSON")

    # --- test ---
    p_test = subparsers.add_parser(
        "test", help="Test if a datetime matches a cron expression"
    )
    p_test.add_argument("expression", help="Cron expression")
    p_test.add_argument("datetime", help="Datetime to test (ISO format)")
    p_test.add_argument("--json", action="store_true", help="Output as JSON")

    # --- build ---
    p_build = subparsers.add_parser(
        "build", help="Build a cron expression from parameters"
    )
    p_build.add_argument("--minute", help="Minute field (e.g., 0, */5, 0,30)")
    p_build.add_argument("--hour", help="Hour field (e.g., 9, */2, 9-17)")
    p_build.add_argument("--day", help="Day-of-month (e.g., 1, 1,15)")
    p_build.add_argument("--month", help="Month (e.g., 1, 1,6)")
    p_build.add_argument(
        "--weekday", help="Weekday (0-6, 'weekdays', 'weekends')"
    )
    p_build.add_argument("--json", action="store_true", help="Output as JSON")

    # --- presets ---
    p_presets = subparsers.add_parser("presets", help="List or look up presets")
    p_presets.add_argument("name", nargs="?", help="Preset name (optional)")
    p_presets.add_argument("--json", action="store_true", help="Output as JSON")

    # --- diff ---
    p_diff = subparsers.add_parser(
        "diff", help="Compare two cron expressions"
    )
    p_diff.add_argument("expression1", help="First cron expression")
    p_diff.add_argument("expression2", help="Second cron expression")
    p_diff.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "explain": _cli_explain,
        "next": _cli_next,
        "previous": _cli_previous,
        "validate": _cli_validate,
        "test": _cli_test,
        "build": _cli_build,
        "presets": _cli_presets,
        "diff": _cli_diff,
    }

    handler = commands.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
