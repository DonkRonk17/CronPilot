# CronPilot - Quick Start Guides

## 📖 ABOUT THESE GUIDES

Each Team Brain agent has a **5-minute quick-start guide** tailored to their role and workflows.

**Choose your guide:**
- [Forge (Orchestrator)](#-forge-quick-start)
- [Atlas (Executor)](#-atlas-quick-start)
- [Clio (Linux Agent)](#-clio-quick-start)
- [Nexus (Multi-Platform)](#-nexus-quick-start)
- [Bolt (Free Executor)](#-bolt-quick-start)
- [Logan (Human-in-the-Loop)](#-logan-quick-start)

---

## 🔥 FORGE QUICK START

**Role:** Orchestrator / Reviewer
**Time:** 5 minutes
**Goal:** Use CronPilot to validate and explain scheduled task configurations

### Step 1: Installation Check
```bash
python cronpilot.py --version
# Expected: cronpilot 1.0.0
```

### Step 2: First Use — Explain an Expression
```bash
python cronpilot.py explain "0 9 * * 1-5"
# At 9:00 AM, Monday through Friday
```

### Step 3: Review Schedule Configs
When reviewing tools or configs that contain cron expressions:

```python
from cronpilot import validate, CronExpression

config_crons = {
    "task_runner": "0 9 * * *",
    "mentorship": "0 10 * * *",
    "nightly_backup": "0 2 * * *",
}

for name, expr in config_crons.items():
    result = validate(expr)
    if result["valid"]:
        cron = CronExpression(expr)
        print(f"[OK] {name}: {cron.explain()}")
        runs = cron.next_runs(3)
        for r in runs:
            print(f"     -> {r.strftime('%Y-%m-%d %H:%M (%A)')}")
    else:
        print(f"[X] {name}: {result['error']}")
```

### Step 4: Compare Expressions During Review
```bash
python cronpilot.py diff "0 9 * * *" "0 9 * * 1-5"
# Shows that first runs every day, second only weekdays
```

### Next Steps for Forge
1. Use `validate()` when reviewing schedule configurations
2. Use `explain()` for natural-language schedule documentation
3. Integrate into orchestration review checklists
4. See [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) — Forge section

---

## ⚡ ATLAS QUICK START

**Role:** Executor / Builder
**Time:** 5 minutes
**Goal:** Use CronPilot when building tools that need scheduling

### Step 1: Installation Check
```bash
python -c "from cronpilot import CronExpression; print('[OK] CronPilot available')"
```

### Step 2: First Use — Build an Expression
```python
from cronpilot import CronBuilder

expr = (CronBuilder()
    .every_n_minutes(15)
    .hour_range(9, 17)
    .on_weekdays()
    .build())
print(f"Built: {expr}")
# Built: */15 9-17 * * 1-5
```

### Step 3: Use in Tool Development
When building a tool that accepts cron input:

```python
from cronpilot import validate, CronExpression

def schedule_task(cron_input: str):
    result = validate(cron_input)
    if not result["valid"]:
        raise ValueError(f"Invalid schedule: {result['error']}")

    cron = CronExpression(cron_input)
    print(f"Scheduled: {cron.explain()}")
    next_run = cron.next_runs(1)[0]
    print(f"Next run: {next_run.strftime('%Y-%m-%d %H:%M')}")
    return cron
```

### Step 4: Add to Test Suites
```python
import unittest
from cronpilot import validate

class TestScheduleInput(unittest.TestCase):
    def test_valid_cron(self):
        result = validate("0 9 * * 1-5")
        self.assertTrue(result["valid"])

    def test_invalid_cron(self):
        result = validate("0 25 * * *")
        self.assertFalse(result["valid"])
```

### Next Steps for Atlas
1. Use CronBuilder in any tool that generates schedules
2. Use validate() in test suites for cron input validation
3. Add to Holy Grail build checklist where scheduling is involved
4. See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) — Pattern 1-3

---

## 🐧 CLIO QUICK START

**Role:** Linux / Ubuntu Agent
**Time:** 5 minutes
**Goal:** Validate and manage crontab entries on Linux

### Step 1: Linux Installation
```bash
git clone https://github.com/DonkRonk17/CronPilot.git
cd CronPilot
python3 cronpilot.py --version
```

### Step 2: First Use — Validate Crontab Entry
```bash
# Before adding to crontab, validate:
python3 cronpilot.py validate "30 2 * * 0"
# [OK] Valid cron expression: 30 2 * * 0
#      Meaning: At 2:30 AM, On Sunday

# See when it fires next:
python3 cronpilot.py next "30 2 * * 0" -n 4
```

### Step 3: Manage Linux Crontab
```bash
# Check what an existing crontab entry does:
python3 cronpilot.py explain "0 */6 * * *"
# At minute 0 of every hour, Every 6 hours

# Build a new entry:
python3 cronpilot.py build --minute 0 --hour 2 --weekday 0
# Expression: 0 2 * * 0 (Sunday 2 AM)

# Add to crontab:
# crontab -e
# 0 2 * * 0 /path/to/backup.sh
```

### Step 4: Common Clio Commands
```bash
# Quick health check schedule
python3 cronpilot.py presets every_5_minutes

# Business hours monitoring
python3 cronpilot.py explain "*/5 9-17 * * 1-5"

# Log rotation schedule
python3 cronpilot.py explain "0 0 * * 0"
```

### Platform-Specific Features
- Works with standard Linux crontab format
- Validates before writing to avoid crontab errors
- Presets match common Linux admin schedules

### Next Steps for Clio
1. Validate all existing crontab entries
2. Use presets for standard admin schedules
3. Add validation step before `crontab -e`
4. See [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md) — Clio section

---

## 🌐 NEXUS QUICK START

**Role:** Multi-Platform Agent
**Time:** 5 minutes
**Goal:** Cross-platform schedule validation and management

### Step 1: Platform Detection
```python
import platform
from cronpilot import CronExpression

print(f"Platform: {platform.system()}")
cron = CronExpression("0 9 * * 1-5")
print(f"Schedule: {cron.explain()}")
# Works identically on Windows, Linux, macOS
```

### Step 2: First Use — Cross-Platform Validation
```python
from cronpilot import validate

expressions = [
    "0 9 * * 1-5",      # Weekday mornings
    "0 2 * * *",         # Nightly backup
    "*/15 * * * *",      # Every 15 minutes
]

for expr in expressions:
    result = validate(expr)
    status = "[OK]" if result["valid"] else "[X]"
    print(f"{status} {expr}: {result.get('explanation', result.get('error'))}")
```

### Step 3: Platform-Specific Considerations

**Windows (Task Scheduler):**
- Windows Task Scheduler uses different format than cron
- CronPilot can still validate the scheduling logic
- Use `next_runs()` to verify timing before configuring Task Scheduler

**Linux (crontab):**
- Direct crontab format compatibility
- Validate before writing

**macOS (launchd):**
- macOS uses launchd plist, not cron
- CronPilot helps define the schedule logic; translate to plist manually

### Step 4: Common Nexus Commands
```bash
# Validate on any platform
python cronpilot.py validate "0 9 * * 1-5"

# Next runs with specific timezone consideration
python cronpilot.py next "0 9 * * 1-5" --after "2026-03-01T00:00:00" -n 10
```

### Next Steps for Nexus
1. Test on all 3 platforms
2. Create platform-specific schedule translation guides
3. Use JSON output for cross-tool integration
4. See [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md) — Pattern 9

---

## 🆓 BOLT QUICK START

**Role:** Free Executor (Cline + Grok)
**Time:** 5 minutes
**Goal:** Quick cron lookups without API costs

### Step 1: Verify Free Access
```bash
# No API key required, no pip install needed!
python cronpilot.py --version
```

### Step 2: First Use — Quick Lookup
```bash
# Don't remember cron syntax? Use presets:
python cronpilot.py presets

# Need a daily 9 AM schedule?
python cronpilot.py presets daily_9am

# Need to understand a cron you found?
python cronpilot.py explain "*/15 9-17 * * 1-5"
```

### Step 3: Build Without Memorizing
```bash
# Just tell it what you want:
python cronpilot.py build --minute 0 --hour 9 --weekday weekdays
# Output: 0 9 * * 1-5

python cronpilot.py build --minute "*/30" --hour "8-18"
# Output: */30 8-18 * * *
```

### Step 4: Common Bolt Commands
```bash
# Quick reference
python cronpilot.py presets

# Validate before using
python cronpilot.py validate "0 9 * * 1-5"

# Check next runs
python cronpilot.py next "0 0 * * *" -n 3
```

### Cost Considerations
- Zero dependencies = zero install cost
- Single file = instant availability
- CLI usage = no API tokens needed
- Presets = no need to construct expressions manually

### Next Steps for Bolt
1. Use presets for quick schedule lookups
2. Add to Cline workflow for cron-related tasks
3. Use build command instead of memorizing syntax
4. Report any issues via Synapse

---

## 👤 LOGAN QUICK START

**Role:** Human-in-the-Loop / Project Owner
**Time:** 3 minutes
**Goal:** Quickly understand or create cron schedules

### Quick Commands

```bash
# "What does this cron do?"
python cronpilot.py explain "0 9 * * 1-5"
# -> At 9:00 AM, Monday through Friday

# "When will this run next?"
python cronpilot.py next "0 9 * * 1-5" -n 7

# "I need a schedule for every 15 minutes during work hours"
python cronpilot.py build --minute "*/15" --hour "9-17" --weekday weekdays
# -> */15 9-17 * * 1-5

# "Show me common schedules"
python cronpilot.py presets

# "Is this cron correct?"
python cronpilot.py validate "0 9 * * 1-5"
```

### Most Useful Presets for Logan
- `daily_9am` — Daily morning automation
- `weekdays` — Weekday-only schedules
- `business_hours` — Active during work hours
- `weekly` — Weekly recurring tasks

---

## 📚 ADDITIONAL RESOURCES

**For All Agents:**
- Full Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Integration Plan: [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)

**Support:**
- GitHub Issues: [https://github.com/DonkRonk17/CronPilot/issues](https://github.com/DonkRonk17/CronPilot/issues)
- Synapse: Post in THE_SYNAPSE/active/
- Direct: Message ATLAS (builder)

---

**Last Updated:** February 22, 2026
**Maintained By:** ATLAS (Team Brain)
