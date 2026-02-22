#!/usr/bin/env python3
"""
Comprehensive test suite for CronPilot.

Tests cover:
- Core parsing and validation
- Explain functionality
- Next/previous run calculation
- Match testing
- Builder API
- Presets
- Diff comparison
- Edge cases and error handling
- CLI interface

Run: python test_cronpilot.py
"""

import datetime
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cronpilot import (
    CronBuilder,
    CronBuildError,
    CronError,
    CronExpression,
    CronParseError,
    CronValidationError,
    get_preset,
    list_presets,
    main,
    validate,
)


class TestCronExpressionParsing(unittest.TestCase):
    """Test cron expression parsing."""

    def test_parse_simple_wildcard(self):
        """Every minute expression."""
        cron = CronExpression("* * * * *")
        self.assertEqual(cron.minutes, list(range(0, 60)))
        self.assertEqual(cron.hours, list(range(0, 24)))
        self.assertEqual(cron.days, list(range(1, 32)))
        self.assertEqual(cron.months, list(range(1, 13)))
        self.assertEqual(cron.weekdays, list(range(0, 7)))

    def test_parse_specific_values(self):
        """Specific minute/hour."""
        cron = CronExpression("30 9 * * *")
        self.assertEqual(cron.minutes, [30])
        self.assertEqual(cron.hours, [9])

    def test_parse_ranges(self):
        """Ranges like 9-17."""
        cron = CronExpression("0 9-17 * * *")
        self.assertEqual(cron.hours, list(range(9, 18)))

    def test_parse_step(self):
        """Step values like */15."""
        cron = CronExpression("*/15 * * * *")
        self.assertEqual(cron.minutes, [0, 15, 30, 45])

    def test_parse_list(self):
        """List values like 1,3,5."""
        cron = CronExpression("0 9 * * 1,3,5")
        self.assertEqual(cron.weekdays, [1, 3, 5])

    def test_parse_range_with_step(self):
        """Range with step like 1-30/5."""
        cron = CronExpression("1-30/5 * * * *")
        self.assertEqual(cron.minutes, [1, 6, 11, 16, 21, 26])

    def test_parse_month_names(self):
        """Month name abbreviations like jan,jun."""
        cron = CronExpression("0 0 1 jan,jun *")
        self.assertEqual(cron.months, [1, 6])

    def test_parse_weekday_names(self):
        """Weekday name abbreviations like mon-fri."""
        cron = CronExpression("0 9 * * mon-fri")
        self.assertEqual(cron.weekdays, [1, 2, 3, 4, 5])

    def test_parse_special_yearly(self):
        """@yearly special expression."""
        cron = CronExpression("@yearly")
        self.assertEqual(cron.minutes, [0])
        self.assertEqual(cron.hours, [0])
        self.assertEqual(cron.days, [1])
        self.assertEqual(cron.months, [1])

    def test_parse_special_monthly(self):
        """@monthly special expression."""
        cron = CronExpression("@monthly")
        self.assertEqual(cron.days, [1])

    def test_parse_special_weekly(self):
        """@weekly special expression."""
        cron = CronExpression("@weekly")
        self.assertEqual(cron.weekdays, [0])  # Sunday

    def test_parse_special_daily(self):
        """@daily and @midnight are equivalent."""
        cron_d = CronExpression("@daily")
        cron_m = CronExpression("@midnight")
        self.assertEqual(cron_d, cron_m)

    def test_parse_special_hourly(self):
        """@hourly special expression."""
        cron = CronExpression("@hourly")
        self.assertEqual(cron.minutes, [0])
        self.assertEqual(cron.hours, list(range(0, 24)))

    def test_parse_complex(self):
        """Complex multi-feature expression."""
        cron = CronExpression("0,30 9-17 1,15 1-6 mon-fri")
        self.assertEqual(cron.minutes, [0, 30])
        self.assertEqual(cron.hours, list(range(9, 18)))
        self.assertEqual(cron.days, [1, 15])
        self.assertEqual(cron.months, [1, 2, 3, 4, 5, 6])
        self.assertEqual(cron.weekdays, [1, 2, 3, 4, 5])


class TestCronExpressionErrors(unittest.TestCase):
    """Test error handling in parsing."""

    def test_empty_expression(self):
        """Empty string raises error."""
        with self.assertRaises(CronParseError):
            CronExpression("")

    def test_none_expression(self):
        """None raises error."""
        with self.assertRaises(CronParseError):
            CronExpression(None)

    def test_too_few_fields(self):
        """Less than 5 fields."""
        with self.assertRaises(CronParseError):
            CronExpression("* * *")

    def test_too_many_fields(self):
        """More than 5 fields."""
        with self.assertRaises(CronParseError):
            CronExpression("* * * * * *")

    def test_invalid_value(self):
        """Non-numeric value."""
        with self.assertRaises(CronParseError):
            CronExpression("abc * * * *")

    def test_out_of_range_minute(self):
        """Minute > 59."""
        with self.assertRaises(CronValidationError):
            CronExpression("60 * * * *")

    def test_out_of_range_hour(self):
        """Hour > 23."""
        with self.assertRaises(CronValidationError):
            CronExpression("0 24 * * *")

    def test_out_of_range_day(self):
        """Day > 31."""
        with self.assertRaises(CronValidationError):
            CronExpression("0 0 32 * *")

    def test_out_of_range_month(self):
        """Month > 12."""
        with self.assertRaises(CronValidationError):
            CronExpression("0 0 * 13 *")

    def test_out_of_range_weekday(self):
        """Weekday > 6."""
        with self.assertRaises(CronValidationError):
            CronExpression("0 0 * * 7")

    def test_reboot_not_schedulable(self):
        """@reboot raises error (not schedulable)."""
        with self.assertRaises(CronParseError):
            CronExpression("@reboot")

    def test_invalid_step_zero(self):
        """Step of 0 raises error."""
        with self.assertRaises(CronValidationError):
            CronExpression("*/0 * * * *")

    def test_negative_step(self):
        """Negative step raises error."""
        with self.assertRaises(CronValidationError):
            CronExpression("*/-1 * * * *")


class TestCronExpressionMatches(unittest.TestCase):
    """Test datetime matching."""

    def test_matches_every_minute(self):
        """Every minute matches any time."""
        cron = CronExpression("* * * * *")
        dt = datetime.datetime(2026, 2, 22, 14, 30)
        self.assertTrue(cron.matches(dt))

    def test_matches_specific_time(self):
        """Specific time matches correctly."""
        cron = CronExpression("30 9 * * *")
        self.assertTrue(cron.matches(datetime.datetime(2026, 2, 22, 9, 30)))
        self.assertFalse(cron.matches(datetime.datetime(2026, 2, 22, 9, 31)))
        self.assertFalse(cron.matches(datetime.datetime(2026, 2, 22, 10, 30)))

    def test_matches_weekday(self):
        """Weekday matching (Mon-Fri)."""
        cron = CronExpression("0 9 * * 1-5")
        # Monday Feb 23, 2026
        self.assertTrue(cron.matches(datetime.datetime(2026, 2, 23, 9, 0)))
        # Sunday Feb 22, 2026
        self.assertFalse(cron.matches(datetime.datetime(2026, 2, 22, 9, 0)))

    def test_matches_specific_day(self):
        """Day-of-month matching."""
        cron = CronExpression("0 0 15 * *")
        self.assertTrue(cron.matches(datetime.datetime(2026, 3, 15, 0, 0)))
        self.assertFalse(cron.matches(datetime.datetime(2026, 3, 14, 0, 0)))

    def test_matches_specific_month(self):
        """Month matching."""
        cron = CronExpression("0 0 1 1 *")
        self.assertTrue(cron.matches(datetime.datetime(2026, 1, 1, 0, 0)))
        self.assertFalse(cron.matches(datetime.datetime(2026, 2, 1, 0, 0)))

    def test_matches_day_or_weekday_union(self):
        """When both day and weekday are restricted, standard cron uses OR (union)."""
        cron = CronExpression("0 0 15 * 1")
        # The 15th OR Mondays
        # March 15 (Sunday) -> day matches
        self.assertTrue(cron.matches(datetime.datetime(2026, 3, 15, 0, 0)))
        # March 16 (Monday) -> weekday matches
        self.assertTrue(cron.matches(datetime.datetime(2026, 3, 16, 0, 0)))
        # March 14 (Saturday) -> neither
        self.assertFalse(cron.matches(datetime.datetime(2026, 3, 14, 0, 0)))

    def test_matches_type_error(self):
        """Non-datetime raises TypeError."""
        cron = CronExpression("* * * * *")
        with self.assertRaises(TypeError):
            cron.matches("2026-02-22")


class TestCronExpressionNextRuns(unittest.TestCase):
    """Test next run calculation."""

    def test_next_runs_count(self):
        """Correct number of results returned."""
        cron = CronExpression("0 * * * *")
        runs = cron.next_runs(count=3)
        self.assertEqual(len(runs), 3)

    def test_next_runs_order(self):
        """Results are in chronological order."""
        cron = CronExpression("0 * * * *")
        runs = cron.next_runs(count=5)
        for i in range(len(runs) - 1):
            self.assertLess(runs[i], runs[i + 1])

    def test_next_runs_after(self):
        """Results are after the 'after' parameter."""
        after = datetime.datetime(2026, 3, 1, 0, 0, 0)
        cron = CronExpression("0 9 * * *")
        runs = cron.next_runs(count=3, after=after)
        for run in runs:
            self.assertGreater(run, after)

    def test_next_runs_every_minute(self):
        """Every minute returns consecutive minutes."""
        after = datetime.datetime(2026, 1, 1, 12, 0, 0)
        cron = CronExpression("* * * * *")
        runs = cron.next_runs(count=3, after=after)
        self.assertEqual(runs[0], datetime.datetime(2026, 1, 1, 12, 1))
        self.assertEqual(runs[1], datetime.datetime(2026, 1, 1, 12, 2))
        self.assertEqual(runs[2], datetime.datetime(2026, 1, 1, 12, 3))

    def test_next_runs_invalid_count(self):
        """Zero or negative count raises error."""
        cron = CronExpression("* * * * *")
        with self.assertRaises(ValueError):
            cron.next_runs(count=0)
        with self.assertRaises(ValueError):
            cron.next_runs(count=-1)


class TestCronExpressionPreviousRuns(unittest.TestCase):
    """Test previous run calculation."""

    def test_previous_runs_count(self):
        """Correct number of results."""
        cron = CronExpression("0 * * * *")
        runs = cron.previous_runs(count=3)
        self.assertEqual(len(runs), 3)

    def test_previous_runs_reverse_order(self):
        """Results are most-recent first."""
        cron = CronExpression("0 * * * *")
        runs = cron.previous_runs(count=5)
        for i in range(len(runs) - 1):
            self.assertGreater(runs[i], runs[i + 1])


class TestCronExpressionExplain(unittest.TestCase):
    """Test human-readable explanations."""

    def test_explain_every_minute(self):
        """Every minute has clean explanation."""
        cron = CronExpression("* * * * *")
        explanation = cron.explain()
        self.assertIn("Every minute", explanation)

    def test_explain_daily_9am(self):
        """Daily at 9am is clear."""
        cron = CronExpression("0 9 * * *")
        explanation = cron.explain()
        self.assertIn("9:00 AM", explanation)

    def test_explain_weekdays(self):
        """Weekday expression mentions Monday through Friday."""
        cron = CronExpression("0 9 * * 1-5")
        explanation = cron.explain()
        self.assertIn("Monday through Friday", explanation)

    def test_explain_step(self):
        """Step pattern mentions interval."""
        cron = CronExpression("*/15 * * * *")
        explanation = cron.explain()
        self.assertIn("15 minutes", explanation)

    def test_explain_specific_month(self):
        """Specific month is named."""
        cron = CronExpression("0 0 1 1 *")
        explanation = cron.explain()
        self.assertIn("January", explanation)

    def test_explain_weekends(self):
        """Weekend expression is clear."""
        cron = CronExpression("0 10 * * 0,6")
        explanation = cron.explain()
        self.assertIn("weekend", explanation.lower())


class TestCronExpressionSerialization(unittest.TestCase):
    """Test JSON and dict serialization."""

    def test_to_dict(self):
        """to_dict includes all fields."""
        cron = CronExpression("0 9 * * 1-5")
        d = cron.to_dict()
        self.assertIn("expression", d)
        self.assertIn("minutes", d)
        self.assertIn("hours", d)
        self.assertIn("days", d)
        self.assertIn("months", d)
        self.assertIn("weekdays", d)
        self.assertIn("explanation", d)

    def test_to_json(self):
        """to_json produces valid JSON."""
        cron = CronExpression("0 9 * * 1-5")
        j = cron.to_json()
        parsed = json.loads(j)
        self.assertEqual(parsed["expression"], "0 9 * * 1-5")

    def test_repr(self):
        """repr format."""
        cron = CronExpression("0 9 * * *")
        self.assertEqual(repr(cron), "CronExpression('0 9 * * *')")

    def test_str(self):
        """str returns original expression."""
        cron = CronExpression("0 9 * * *")
        self.assertEqual(str(cron), "0 9 * * *")


class TestCronExpressionEquality(unittest.TestCase):
    """Test equality comparison."""

    def test_equal_same_expression(self):
        """Same expression is equal."""
        a = CronExpression("0 9 * * 1-5")
        b = CronExpression("0 9 * * 1-5")
        self.assertEqual(a, b)

    def test_equal_different_format(self):
        """Different format but same schedule is equal."""
        a = CronExpression("0 9 * * mon-fri")
        b = CronExpression("0 9 * * 1-5")
        self.assertEqual(a, b)

    def test_not_equal_different(self):
        """Different schedules are not equal."""
        a = CronExpression("0 9 * * *")
        b = CronExpression("0 10 * * *")
        self.assertNotEqual(a, b)

    def test_not_equal_non_cron(self):
        """Comparison with non-CronExpression."""
        cron = CronExpression("0 9 * * *")
        self.assertNotEqual(cron, "0 9 * * *")


class TestCronBuilder(unittest.TestCase):
    """Test the CronBuilder API."""

    def test_build_default(self):
        """Default builder produces every-minute."""
        builder = CronBuilder()
        self.assertEqual(builder.build(), "* * * * *")

    def test_build_specific_time(self):
        """Build specific time."""
        builder = CronBuilder()
        expr = builder.at_minute(0).at_hours(9).build()
        self.assertEqual(expr, "0 9 * * *")

    def test_build_every_n_minutes(self):
        """Every N minutes."""
        builder = CronBuilder()
        expr = builder.every_n_minutes(15).build()
        self.assertEqual(expr, "*/15 * * * *")

    def test_build_weekdays(self):
        """Weekday schedule."""
        builder = CronBuilder()
        expr = builder.at_minute(0).at_hours(9).on_weekdays().build()
        self.assertEqual(expr, "0 9 * * 1-5")

    def test_build_weekends(self):
        """Weekend schedule."""
        builder = CronBuilder()
        expr = builder.at_minute(0).at_hours(10).on_weekends().build()
        self.assertEqual(expr, "0 10 * * 0,6")

    def test_build_hour_range(self):
        """Hour range."""
        builder = CronBuilder()
        expr = builder.at_minute(0).hour_range(9, 17).build()
        self.assertEqual(expr, "0 9-17 * * *")

    def test_build_specific_days(self):
        """Specific days of month."""
        builder = CronBuilder()
        expr = builder.at_minute(0).at_hours(0).on_days(1, 15).build()
        self.assertEqual(expr, "0 0 1,15 * *")

    def test_build_specific_months(self):
        """Specific months."""
        builder = CronBuilder()
        expr = builder.at_minute(0).at_hours(0).on_days(1).in_months(1, 4, 7, 10).build()
        self.assertEqual(expr, "0 0 1 1,4,7,10 *")

    def test_build_chaining(self):
        """Fluent chaining API."""
        expr = (CronBuilder()
                .every_n_minutes(5)
                .hour_range(9, 17)
                .on_weekdays()
                .build())
        self.assertEqual(expr, "*/5 9-17 * * 1-5")

    def test_build_explained(self):
        """build_explained returns tuple."""
        builder = CronBuilder().at_minute(0).at_hours(9)
        expr, explanation = builder.build_explained()
        self.assertEqual(expr, "0 9 * * *")
        self.assertIn("9:00 AM", explanation)

    def test_build_reset(self):
        """Reset clears all fields."""
        builder = CronBuilder()
        builder.at_minute(30).at_hours(12)
        builder.reset()
        self.assertEqual(builder.build(), "* * * * *")

    def test_build_invalid_minute(self):
        """Out of range minute raises error."""
        builder = CronBuilder()
        with self.assertRaises(CronBuildError):
            builder.at_minute(60)

    def test_build_invalid_hour(self):
        """Out of range hour raises error."""
        builder = CronBuilder()
        with self.assertRaises(CronBuildError):
            builder.at_hours(25)

    def test_build_invalid_day(self):
        """Out of range day raises error."""
        builder = CronBuilder()
        with self.assertRaises(CronBuildError):
            builder.on_days(0)

    def test_build_invalid_month(self):
        """Out of range month raises error."""
        builder = CronBuilder()
        with self.assertRaises(CronBuildError):
            builder.in_months(13)

    def test_build_invalid_weekday(self):
        """Out of range weekday raises error."""
        builder = CronBuilder()
        with self.assertRaises(CronBuildError):
            builder.on_specific_weekdays(7)


class TestValidate(unittest.TestCase):
    """Test the validate() function."""

    def test_validate_valid(self):
        """Valid expression returns valid=True."""
        result = validate("0 9 * * 1-5")
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])
        self.assertIsNotNone(result["explanation"])
        self.assertIsNotNone(result["fields"])

    def test_validate_invalid(self):
        """Invalid expression returns valid=False."""
        result = validate("bad cron expression")
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["error"])

    def test_validate_fields(self):
        """Fields are returned for valid expressions."""
        result = validate("0 9 1 1 *")
        self.assertEqual(result["fields"]["minute"], "0")
        self.assertEqual(result["fields"]["hour"], "9")
        self.assertEqual(result["fields"]["day"], "1")
        self.assertEqual(result["fields"]["month"], "1")
        self.assertEqual(result["fields"]["weekday"], "*")


class TestPresets(unittest.TestCase):
    """Test preset functionality."""

    def test_list_presets(self):
        """All presets are returned."""
        presets = list_presets()
        self.assertGreater(len(presets), 10)

    def test_get_preset_exists(self):
        """Known preset returns data."""
        preset = get_preset("daily")
        self.assertIsNotNone(preset)
        self.assertEqual(preset["expression"], "0 0 * * *")

    def test_get_preset_not_found(self):
        """Unknown preset returns None."""
        preset = get_preset("nonexistent")
        self.assertIsNone(preset)

    def test_all_presets_valid(self):
        """Every preset is a valid cron expression (except @reboot)."""
        for name, info in list_presets().items():
            if info["expression"] == "@reboot":
                continue
            try:
                CronExpression(info["expression"])
            except CronError:
                self.fail(f"Preset '{name}' has invalid expression: {info['expression']}")


class TestCLI(unittest.TestCase):
    """Test CLI interface via main()."""

    def test_cli_no_args(self):
        """No arguments prints help (exit 0)."""
        result = main([])
        self.assertEqual(result, 0)

    def test_cli_version(self):
        """--version exits normally."""
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cli_explain(self):
        """explain command works."""
        result = main(["explain", "0 9 * * 1-5"])
        self.assertEqual(result, 0)

    def test_cli_explain_invalid(self):
        """explain with invalid expression returns 1."""
        result = main(["explain", "bad"])
        self.assertEqual(result, 1)

    def test_cli_validate_valid(self):
        """validate valid expression returns 0."""
        result = main(["validate", "0 9 * * *"])
        self.assertEqual(result, 0)

    def test_cli_validate_invalid(self):
        """validate invalid expression returns 1."""
        result = main(["validate", "bad"])
        self.assertEqual(result, 1)

    def test_cli_next(self):
        """next command works."""
        result = main(["next", "0 * * * *", "-n", "3"])
        self.assertEqual(result, 0)

    def test_cli_previous(self):
        """previous command works."""
        result = main(["previous", "0 * * * *", "-n", "3"])
        self.assertEqual(result, 0)

    def test_cli_test_match(self):
        """test command with matching datetime."""
        result = main(["test", "0 9 * * 1", "2026-02-23T09:00:00"])
        self.assertEqual(result, 0)

    def test_cli_test_no_match(self):
        """test command with non-matching datetime returns 0 (still valid operation)."""
        result = main(["test", "0 9 * * 1", "2026-02-22T09:00:00"])
        self.assertEqual(result, 0)

    def test_cli_build(self):
        """build command works."""
        result = main(["build", "--minute", "0", "--hour", "9", "--weekday", "weekdays"])
        self.assertEqual(result, 0)

    def test_cli_presets_list(self):
        """presets command lists all."""
        result = main(["presets"])
        self.assertEqual(result, 0)

    def test_cli_presets_specific(self):
        """presets command for specific preset."""
        result = main(["presets", "daily"])
        self.assertEqual(result, 0)

    def test_cli_diff(self):
        """diff command works."""
        result = main(["diff", "0 9 * * *", "0 10 * * *"])
        self.assertEqual(result, 0)

    def test_cli_explain_json(self):
        """explain --json produces valid JSON."""
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            result = main(["explain", "0 9 * * 1-5", "--json"])
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        self.assertEqual(result, 0)
        data = json.loads(output)
        self.assertEqual(data["expression"], "0 9 * * 1-5")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases."""

    def test_minute_zero(self):
        """Minute 0 is valid."""
        cron = CronExpression("0 0 * * *")
        self.assertEqual(cron.minutes, [0])

    def test_day_31(self):
        """Day 31 is valid."""
        cron = CronExpression("0 0 31 * *")
        self.assertEqual(cron.days, [31])

    def test_month_december(self):
        """Month 12 (December)."""
        cron = CronExpression("0 0 * 12 *")
        self.assertEqual(cron.months, [12])

    def test_weekday_sunday_zero(self):
        """Sunday as 0."""
        cron = CronExpression("0 0 * * 0")
        self.assertEqual(cron.weekdays, [0])

    def test_whitespace_handling(self):
        """Extra whitespace around expression."""
        cron = CronExpression("  0 9 * * *  ")
        self.assertEqual(cron.minutes, [0])

    def test_large_next_runs(self):
        """Large count for next_runs."""
        cron = CronExpression("0 0 * * *")
        runs = cron.next_runs(count=100)
        self.assertEqual(len(runs), 100)

    def test_count_exceeds_limit(self):
        """Count > 1000 raises error."""
        cron = CronExpression("* * * * *")
        with self.assertRaises(ValueError):
            cron.next_runs(count=1001)

    def test_multiple_values_all_fields(self):
        """Multiple values in all fields."""
        cron = CronExpression("0,30 9,17 1,15 1,7 1,5")
        self.assertEqual(cron.minutes, [0, 30])
        self.assertEqual(cron.hours, [9, 17])
        self.assertEqual(cron.days, [1, 15])
        self.assertEqual(cron.months, [1, 7])
        self.assertEqual(cron.weekdays, [1, 5])

    def test_annually_alias(self):
        """@annually same as @yearly."""
        a = CronExpression("@annually")
        b = CronExpression("@yearly")
        self.assertEqual(a, b)


def run_tests():
    """Run all tests with summary."""
    print("=" * 70)
    print("TESTING: CronPilot v1.0")
    print("=" * 70)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestCronExpressionParsing,
        TestCronExpressionErrors,
        TestCronExpressionMatches,
        TestCronExpressionNextRuns,
        TestCronExpressionPreviousRuns,
        TestCronExpressionExplain,
        TestCronExpressionSerialization,
        TestCronExpressionEquality,
        TestCronBuilder,
        TestValidate,
        TestPresets,
        TestCLI,
        TestEdgeCases,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"RESULTS: {result.testsRun} tests")
    print(f"[OK] Passed: {passed}")
    if result.failures:
        print(f"[X] Failed: {len(result.failures)}")
    if result.errors:
        print(f"[X] Errors: {len(result.errors)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
