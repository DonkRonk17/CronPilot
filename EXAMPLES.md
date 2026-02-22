# CronPilot - Usage Examples

Quick navigation:
- [Example 1: Basic Expression Explanation](#example-1-basic-expression-explanation)
- [Example 2: Validating Before Deployment](#example-2-validating-before-deployment)
- [Example 3: Preview Next Run Times](#example-3-preview-next-run-times)
- [Example 4: Building From Parameters](#example-4-building-from-parameters)
- [Example 5: Testing Specific Datetimes](#example-5-testing-specific-datetimes)
- [Example 6: Using Presets](#example-6-using-presets)
- [Example 7: Comparing Two Expressions](#example-7-comparing-two-expressions)
- [Example 8: Python API — Full Workflow](#example-8-python-api--full-workflow)
- [Example 9: JSON Output for Automation](#example-9-json-output-for-automation)
- [Example 10: Complex Real-World Schedules](#example-10-complex-real-world-schedules)
- [Example 11: CronBuilder Fluent API](#example-11-cronbuilder-fluent-api)
- [Example 12: Error Handling & Recovery](#example-12-error-handling--recovery)

---

## Example 1: Basic Expression Explanation

**Scenario:** You found a cron expression in a config file and need to understand it.

**Steps:**
```bash
python cronpilot.py explain "0 9 * * 1-5"
```

**Expected Output:**
```
Expression: 0 9 * * 1-5
Meaning:    At 9:00 AM, Monday through Friday

Parsed fields:
  Minute:  0          -> [0]
  Hour:    9          -> [9]
  Day:     *          -> [1, 2, 3, ..., 31]
  Month:   *          -> [1, 2, 3, ..., 12]
  Weekday: 1-5        -> [1, 2, 3, 4, 5]
```

**What You Learned:**
- Each field is broken down individually
- Weekday 1-5 = Monday through Friday
- The explanation is human-readable

---

## Example 2: Validating Before Deployment

**Scenario:** You're about to deploy a new cron job and want to make sure the syntax is correct.

**Steps:**
```bash
# Valid expression
python cronpilot.py validate "*/15 9-17 * * 1-5"

# Invalid expression (hour 25 doesn't exist)
python cronpilot.py validate "0 25 * * *"

# Invalid expression (wrong number of fields)
python cronpilot.py validate "0 9 *"
```

**Expected Output:**
```
[OK] Valid cron expression: */15 9-17 * * 1-5
     Meaning: Every 15 minutes, 9:00 AM through 5:00 PM, Monday through Friday

[X] Invalid: hour value 25 out of range (0-23)

[X] Invalid: Expected 5 fields (minute hour day month weekday), got 3: '0 9 *'
```

**What You Learned:**
- Validation catches range errors with specific messages
- Field count errors are clearly reported
- Valid expressions get an explanation as bonus

---

## Example 3: Preview Next Run Times

**Scenario:** You want to see exactly when a job will run next before deploying.

**Steps:**
```bash
# Next 7 weekday mornings
python cronpilot.py next "0 9 * * 1-5" -n 7

# Next 3 quarterly runs
python cronpilot.py next "0 0 1 1,4,7,10 *" -n 3

# Runs after a specific date
python cronpilot.py next "0 0 * * 0" --after "2026-06-01T00:00:00" -n 4
```

**Expected Output:**
```
Expression: 0 9 * * 1-5
Meaning:    At 9:00 AM, Monday through Friday

Next 7 runs:
   1. 2026-02-23 09:00  (Monday)
   2. 2026-02-24 09:00  (Tuesday)
   3. 2026-02-25 09:00  (Wednesday)
   4. 2026-02-26 09:00  (Thursday)
   5. 2026-02-27 09:00  (Friday)
   6. 2026-03-02 09:00  (Monday)
   7. 2026-03-03 09:00  (Tuesday)
```

**What You Learned:**
- `-n` controls the number of results
- `--after` lets you simulate from a specific date
- Each run shows the day name for easy verification

---

## Example 4: Building From Parameters

**Scenario:** You know what schedule you want but don't want to memorize cron syntax.

**Steps:**
```bash
# Every day at 9 AM on weekdays
python cronpilot.py build --minute 0 --hour 9 --weekday weekdays

# Every 15 minutes during business hours
python cronpilot.py build --minute "*/15" --hour "9-17" --weekday weekdays

# First of every quarter
python cronpilot.py build --minute 0 --hour 0 --day 1 --month "1,4,7,10"

# Twice daily
python cronpilot.py build --minute 0 --hour "8,20"
```

**Expected Output:**
```
Expression: 0 9 * * 1-5
Meaning:    At 9:00 AM, Monday through Friday

Expression: */15 9-17 * * 1-5
Meaning:    Every 15 minutes, 9:00 AM through 5:00 PM, Monday through Friday

Expression: 0 0 1 1,4,7,10 *
Meaning:    At 12:00 AM, On the 1st, In January, April, July, October

Expression: 0 8,20 * * *
Meaning:    At 8:00 AM and 8:00 PM
```

**What You Learned:**
- `--weekday weekdays` translates to `1-5`
- `--weekday weekends` translates to `0,6`
- Parameters accept the same syntax as raw cron fields

---

## Example 5: Testing Specific Datetimes

**Scenario:** You need to verify whether a specific time would trigger your cron job.

**Steps:**
```bash
# Monday at 9 AM — should match weekday schedule
python cronpilot.py test "0 9 * * 1-5" "2026-02-23T09:00:00"

# Sunday at 9 AM — should NOT match weekday schedule
python cronpilot.py test "0 9 * * 1-5" "2026-02-22T09:00:00"

# Jan 1 at midnight — should match yearly
python cronpilot.py test "0 0 1 1 *" "2026-01-01T00:00:00"
```

**Expected Output:**
```
[OK] MATCH: 2026-02-23 09:00 (Monday)
     matches '0 9 * * 1-5'
    Cron meaning: At 9:00 AM, Monday through Friday

[X] NO MATCH: 2026-02-22 09:00 (Sunday)
    does not match '0 9 * * 1-5'
    Cron meaning: At 9:00 AM, Monday through Friday

[OK] MATCH: 2026-01-01 00:00 (Thursday)
     matches '0 0 1 1 *'
    Cron meaning: At 12:00 AM, On the 1st, In January
```

**What You Learned:**
- MATCH/NO MATCH gives instant feedback
- The day name helps you verify weekday logic
- Works with any ISO-format datetime

---

## Example 6: Using Presets

**Scenario:** You want a common schedule and don't want to write it from scratch.

**Steps:**
```bash
# List all available presets
python cronpilot.py presets

# Get details on a specific preset
python cronpilot.py presets business_hours

# Get details on daily
python cronpilot.py presets daily_9am
```

**Expected Output:**
```
Available Cron Presets:
----------------------------------------------------------------------
  every_minute      * * * * *           Every minute
  every_5_minutes   */5 * * * *         Every 5 minutes
  hourly            0 * * * *           Every hour at minute 0
  daily             0 0 * * *           Every day at midnight
  daily_9am         0 9 * * *           Every day at 9:00 AM
  weekdays          0 9 * * 1-5         Weekdays at 9:00 AM
  business_hours    0 9-17 * * 1-5      Every hour 9 AM - 5 PM on weekdays
  ...
----------------------------------------------------------------------
Total: 20 presets

Preset:     business_hours
Expression: 0 9-17 * * 1-5
Meaning:    Every hour 9 AM - 5 PM on weekdays

Next 3 runs:
  1. 2026-02-23 09:00  (Monday)
  2. 2026-02-23 10:00  (Monday)
  3. 2026-02-23 11:00  (Monday)
```

**What You Learned:**
- 20 presets cover common scheduling needs
- Each preset shows next runs when queried individually
- Preset names use underscores (e.g., `daily_9am`)

---

## Example 7: Comparing Two Expressions

**Scenario:** You have two cron expressions and need to know if they produce the same schedule.

**Steps:**
```bash
# These are functionally different
python cronpilot.py diff "0 9 * * *" "0 9 * * 1-5"

# These use different syntax but mean the same thing
python cronpilot.py diff "0 9 * * mon-fri" "0 9 * * 1-5"
```

**Expected Output:**
```
Expression 1: 0 9 * * *
  Meaning:    At 9:00 AM
Expression 2: 0 9 * * 1-5
  Meaning:    At 9:00 AM, Monday through Friday

[!] These expressions are DIFFERENT

Field differences:
   weekday:          * vs 1-5

---

Expression 1: 0 9 * * mon-fri
  Meaning:    At 9:00 AM, Monday through Friday
Expression 2: 0 9 * * 1-5
  Meaning:    At 9:00 AM, Monday through Friday

[OK] These expressions are functionally EQUIVALENT
```

**What You Learned:**
- `diff` compares the actual expanded values, not just strings
- Name aliases (mon-fri) and numbers (1-5) are correctly compared
- EQUIVALENT vs DIFFERENT is clearly indicated

---

## Example 8: Python API — Full Workflow

**Scenario:** You're building an automation script and need programmatic cron support.

**Steps:**
```python
from cronpilot import CronExpression, CronBuilder, validate, get_preset
import datetime

# 1. Validate user input
user_cron = "0 9 * * 1-5"
result = validate(user_cron)
if not result["valid"]:
    print(f"Invalid: {result['error']}")
    exit(1)

# 2. Parse and explain
cron = CronExpression(user_cron)
print(f"Schedule: {cron.explain()}")

# 3. Check next runs
print("\nUpcoming runs:")
for run in cron.next_runs(5):
    print(f"  {run.strftime('%Y-%m-%d %H:%M (%A)')}")

# 4. Test current time
now = datetime.datetime.now()
if cron.matches(now):
    print(f"\n[OK] Current time matches schedule!")
else:
    next_run = cron.next_runs(1)[0]
    diff = next_run - now
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    print(f"\nNext run in {hours}h {minutes}m")

# 5. Build a new schedule
new_schedule = (CronBuilder()
    .every_n_minutes(30)
    .hour_range(8, 18)
    .on_weekdays()
    .build())
print(f"\nNew schedule: {new_schedule}")
print(f"Meaning: {CronExpression(new_schedule).explain()}")
```

**Expected Output:**
```
Schedule: At 9:00 AM, Monday through Friday

Upcoming runs:
  2026-02-23 09:00 (Monday)
  2026-02-24 09:00 (Tuesday)
  2026-02-25 09:00 (Wednesday)
  2026-02-26 09:00 (Thursday)
  2026-02-27 09:00 (Friday)

Next run in 4h 57m

New schedule: */30 8-18 * * 1-5
Meaning: Every 30 minutes, 8:00 AM through 6:00 PM, Monday through Friday
```

**What You Learned:**
- Full validate -> parse -> query -> build workflow
- All functionality available as Python API
- Type-safe with proper error handling

---

## Example 9: JSON Output for Automation

**Scenario:** You need machine-readable output for a CI/CD pipeline or monitoring script.

**Steps:**
```bash
# JSON explanation
python cronpilot.py explain "0 9 * * 1-5" --json

# JSON next runs
python cronpilot.py next "0 9 * * 1-5" -n 3 --json

# JSON validation
python cronpilot.py validate "0 25 * * *" --json
```

**Expected Output:**
```json
{
  "expression": "0 9 * * 1-5",
  "minutes": [0],
  "hours": [9],
  "days": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31],
  "months": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "weekdays": [1, 2, 3, 4, 5],
  "explanation": "At 9:00 AM, Monday through Friday"
}
```

```json
{
  "valid": false,
  "expression": "0 25 * * *",
  "error": "hour value 25 out of range (0-23)",
  "explanation": null,
  "fields": null
}
```

**What You Learned:**
- Every command supports `--json`
- JSON output includes all parsed data
- Perfect for piping into other tools: `cronpilot next "..." --json | jq '.next_runs'`

---

## Example 10: Complex Real-World Schedules

**Scenario:** Setting up production schedules for various automation tasks.

**Steps:**
```bash
# Database backup: 2 AM daily
python cronpilot.py explain "0 2 * * *"
python cronpilot.py next "0 2 * * *" -n 7

# Report generation: 9 AM on 1st and 15th
python cronpilot.py explain "0 9 1,15 * *"

# Health checks: every 5 minutes during business hours
python cronpilot.py explain "*/5 9-17 * * 1-5"

# Quarterly cleanup: midnight on first of quarter
python cronpilot.py explain "0 0 1 1,4,7,10 *"

# Weekend maintenance: Saturday 3 AM
python cronpilot.py explain "0 3 * * 6"
```

**Expected Output:**
```
Expression: 0 2 * * *
Meaning:    At 2:00 AM

Expression: 0 9 1,15 * *
Meaning:    At 9:00 AM, On days 1, 15

Expression: */5 9-17 * * 1-5
Meaning:    Every 5 minutes, 9:00 AM through 5:00 PM, Monday through Friday

Expression: 0 0 1 1,4,7,10 *
Meaning:    At 12:00 AM, On the 1st, In January, April, July, October

Expression: 0 3 * * 6
Meaning:    At 3:00 AM, On Saturday
```

**What You Learned:**
- Real production schedules are easy to validate
- Complex expressions produce clear explanations
- Multiple time components combine naturally

---

## Example 11: CronBuilder Fluent API

**Scenario:** Building schedules programmatically in a configuration system.

**Steps:**
```python
from cronpilot import CronBuilder, CronExpression

# Build various schedules
schedules = {
    "health_check": (CronBuilder()
        .every_n_minutes(5)
        .build()),
    "daily_report": (CronBuilder()
        .at_minute(0)
        .at_hours(9)
        .on_weekdays()
        .build()),
    "weekly_backup": (CronBuilder()
        .at_minute(0)
        .at_hours(2)
        .on_specific_weekdays(0)  # Sunday
        .build()),
    "quarterly_review": (CronBuilder()
        .at_minute(0)
        .at_hours(9)
        .on_days(1)
        .in_months(1, 4, 7, 10)
        .build()),
}

for name, expr in schedules.items():
    cron = CronExpression(expr)
    print(f"{name:20s} {expr:20s} {cron.explain()}")
```

**Expected Output:**
```
health_check         */5 * * * *          Every 5 minutes
daily_report         0 9 * * 1-5         At 9:00 AM, Monday through Friday
weekly_backup        0 2 * * 0           At 2:00 AM, On Sunday
quarterly_review     0 9 1 1,4,7,10 *    At 9:00 AM, On the 1st, In January, April, July, October
```

**What You Learned:**
- Builder API is chainable and readable
- Each method validates inputs immediately
- `build()` produces a valid cron string
- Combine with CronExpression for explanation

---

## Example 12: Error Handling & Recovery

**Scenario:** Handling invalid input gracefully in your application.

**Steps:**
```python
from cronpilot import CronExpression, CronParseError, CronValidationError, validate

# Method 1: Try/except with specific errors
expressions = [
    "0 9 * * 1-5",     # Valid
    "bad expression",    # Parse error
    "0 25 * * *",       # Validation error
    "* * *",            # Wrong field count
]

for expr in expressions:
    try:
        cron = CronExpression(expr)
        print(f"[OK] {expr} -> {cron.explain()}")
    except CronParseError as e:
        print(f"[X] Parse error: {e}")
    except CronValidationError as e:
        print(f"[X] Validation error: {e}")

# Method 2: Using validate() function (no exceptions)
for expr in expressions:
    result = validate(expr)
    status = "[OK]" if result["valid"] else "[X]"
    msg = result["explanation"] if result["valid"] else result["error"]
    print(f"{status} {expr}: {msg}")
```

**Expected Output:**
```
[OK] 0 9 * * 1-5 -> At 9:00 AM, Monday through Friday
[X] Parse error: Expected 5 fields (minute hour day month weekday), got 2: 'bad expression'
[X] Validation error: hour value 25 out of range (0-23)
[X] Parse error: Expected 5 fields (minute hour day month weekday), got 3: '* * *'

[OK] 0 9 * * 1-5: At 9:00 AM, Monday through Friday
[X] bad expression: Expected 5 fields (minute hour day month weekday), got 2: 'bad expression'
[X] 0 25 * * *: hour value 25 out of range (0-23)
[X] * * *: Expected 5 fields (minute hour day month weekday), got 3: '* * *'
```

**What You Learned:**
- Two approaches: exceptions or validate() dict
- Specific exception types for different error categories
- validate() never throws — safe for batch processing
- Error messages are descriptive and actionable

---

## 📚 Additional Resources

- Full Documentation: [README.md](README.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)
- Integration Plan: [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)
- Quick Start Guides: [QUICK_START_GUIDES.md](QUICK_START_GUIDES.md)
- GitHub: [https://github.com/DonkRonk17/CronPilot](https://github.com/DonkRonk17/CronPilot)

---

**Last Updated:** February 22, 2026
**Maintained By:** ATLAS (Team Brain)
