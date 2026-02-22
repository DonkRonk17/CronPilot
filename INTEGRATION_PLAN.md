# CronPilot - Integration Plan

## 🎯 INTEGRATION GOALS

This document outlines how CronPilot integrates with:
1. Team Brain agents (Forge, Atlas, Clio, Nexus, Bolt)
2. Existing Team Brain tools
3. BCH (Beacon Command Hub)
4. Logan's workflows

---

## 📦 BCH INTEGRATION

### Overview
CronPilot can serve as the scheduling engine for BCH task automation. While BCH currently uses its own task runner for scheduled events, CronPilot provides the parsing and validation layer.

### BCH Commands (Potential)
```
@cronpilot explain "0 9 * * 1-5"
@cronpilot validate "*/15 * * * *"
@cronpilot next "0 9 * * 1-5" -n 5
```

### Implementation Steps
1. Import CronPilot in BCH backend
2. Use `validate()` for user-submitted schedules
3. Use `CronExpression.explain()` for schedule descriptions in status messages
4. Use `CronExpression.next_runs()` for "next check-in" predictions
5. Use `CronExpression.matches()` in the task runner loop

### BCH Task Runner Integration
```python
from cronpilot import CronExpression
import datetime

class BCHTaskRunner:
    def __init__(self):
        self.tasks = {}

    def register_task(self, name, cron_expr, callback):
        cron = CronExpression(cron_expr)
        self.tasks[name] = {"cron": cron, "callback": callback}

    def tick(self):
        now = datetime.datetime.now()
        for name, task in self.tasks.items():
            if task["cron"].matches(now):
                task["callback"]()
```

---

## 🤖 AI AGENT INTEGRATION

### Integration Matrix

| Agent | Use Case | Integration Method | Priority |
|-------|----------|-------------------|----------|
| **Forge** | Validate scheduled task expressions, explain schedules in reviews | Python API | HIGH |
| **Atlas** | Build cron expressions during tool creation, validate in testing | CLI + Python API | HIGH |
| **Clio** | Manage crontab entries on Linux systems, validate user crons | CLI | HIGH |
| **Nexus** | Cross-platform schedule validation and explanation | Python API | MEDIUM |
| **Bolt** | Quick cron lookups, preset usage for common schedules | CLI | MEDIUM |

### Agent-Specific Workflows

#### Forge (Orchestrator / Reviewer)
**Primary Use Case:** Review and validate scheduled task configurations across Team Brain.

**Integration Steps:**
1. Import CronPilot in review sessions
2. Validate cron expressions in config files during code review
3. Explain schedules in natural language for documentation
4. Compare expressions when reviewing schedule changes

**Example Workflow:**
```python
from cronpilot import CronExpression, validate

def review_schedule_config(config):
    for task_name, cron_str in config["schedules"].items():
        result = validate(cron_str)
        if not result["valid"]:
            return f"[X] Task '{task_name}' has invalid cron: {result['error']}"

        cron = CronExpression(cron_str)
        print(f"[OK] {task_name}: {cron.explain()}")
        runs = cron.next_runs(3)
        print(f"    Next 3 runs: {[r.strftime('%Y-%m-%d %H:%M') for r in runs]}")
    return "[OK] All schedules valid"
```

#### Atlas (Executor / Builder)
**Primary Use Case:** Build scheduling components into new tools, validate cron fields.

**Integration Steps:**
1. Use CronBuilder when creating tools that need scheduling
2. Use validate() in test suites for schedule inputs
3. Use explain() in tool documentation generation

**Example Workflow:**
```python
from cronpilot import CronBuilder, CronExpression

def create_monitoring_schedule(interval_minutes, business_hours_only=False):
    builder = CronBuilder().every_n_minutes(interval_minutes)
    if business_hours_only:
        builder.hour_range(9, 17).on_weekdays()
    expr = builder.build()
    cron = CronExpression(expr)
    return {"expression": expr, "description": cron.explain()}
```

#### Clio (Linux / Ubuntu Agent)
**Primary Use Case:** Manage Linux crontab entries, validate before writing.

**Platform Considerations:**
- Linux crontab uses the same 5-field format
- Clio can validate entries before `crontab -e`
- Can generate crontab lines from presets

**Example:**
```bash
# Validate before adding to crontab
python3 cronpilot.py validate "*/5 * * * *"

# Generate and explain a schedule
python3 cronpilot.py build --minute "*/5" --hour "9-17"

# Check when a crontab entry will next fire
python3 cronpilot.py next "30 2 * * 0" -n 4
```

#### Nexus (Multi-Platform Agent)
**Primary Use Case:** Cross-platform schedule management and documentation.

**Cross-Platform Notes:**
- CronPilot works identically on all platforms
- Windows Task Scheduler uses different format — CronPilot can still explain the logic
- Output is ASCII-safe for all terminal environments

#### Bolt (Cline / Free Executor)
**Primary Use Case:** Quick cron lookups and preset usage without API costs.

**Cost Considerations:**
- Zero dependencies = instant usage, no install time
- Presets reduce the need for expression construction
- CLI usage requires no API tokens

---

## 🔗 INTEGRATION WITH OTHER TEAM BRAIN TOOLS

### With BatchRunner
**Correlation Use Case:** Trigger batch jobs on cron schedules.

**Integration Pattern:**
```python
from cronpilot import CronExpression
import datetime

schedules = {
    "nightly_backup": CronExpression("0 2 * * *"),
    "hourly_sync": CronExpression("0 * * * *"),
    "weekly_report": CronExpression("0 9 * * 1"),
}

now = datetime.datetime.now()
for name, cron in schedules.items():
    if cron.matches(now):
        print(f"[OK] Triggering: {name}")
        # batch_runner.execute(name)
    else:
        next_run = cron.next_runs(1)[0]
        print(f"[--] {name}: next at {next_run.strftime('%Y-%m-%d %H:%M')}")
```

### With TaskTimer
**Task Scheduling Use Case:** Schedule Pomodoro breaks and focus sessions.

**Integration Pattern:**
```python
from cronpilot import CronExpression
import datetime

focus_schedule = CronExpression("0,25,50 9-17 * * 1-5")
break_schedule = CronExpression("25,50 9-17 * * 1-5")

now = datetime.datetime.now()
next_focus = focus_schedule.next_runs(1, after=now)[0]
next_break = break_schedule.next_runs(1, after=now)[0]

print(f"Next focus session: {next_focus.strftime('%H:%M')}")
print(f"Next break: {next_break.strftime('%H:%M')}")
```

### With ServiceMonitor
**Health Check Scheduling Use Case:** Define health check intervals.

**Integration Pattern:**
```python
from cronpilot import CronExpression
import datetime

health_checks = {
    "api_endpoint": CronExpression("*/5 * * * *"),
    "database": CronExpression("*/15 * * * *"),
    "disk_space": CronExpression("0 * * * *"),
    "full_system": CronExpression("0 0 * * *"),
}

now = datetime.datetime.now()
for service, cron in health_checks.items():
    if cron.matches(now):
        print(f"[CHECK] Running health check: {service}")
```

### With SynapseLink
**Scheduled Notifications Use Case:** Send team notifications on schedule.

**Integration Pattern:**
```python
from cronpilot import CronExpression
from synapselink import quick_send
import datetime

weekly_standup = CronExpression("0 9 * * 1")  # Monday 9 AM

if weekly_standup.matches(datetime.datetime.now()):
    quick_send(
        "TEAM",
        "Weekly Standup Reminder",
        "Time for weekly status update! Share your progress.",
        priority="NORMAL"
    )
```

### With AgentHeartbeat
**Heartbeat Scheduling Use Case:** Configure agent check-in intervals.

**Integration Pattern:**
```python
from cronpilot import CronExpression, get_preset
import datetime

heartbeat_schedule = CronExpression(get_preset("every_5_minutes")["expression"])
status_report = CronExpression("0 9,17 * * 1-5")

now = datetime.datetime.now()
if heartbeat_schedule.matches(now):
    send_heartbeat()
if status_report.matches(now):
    send_status_report()
```

### With TaskQueuePro
**Queue Processing Use Case:** Process task queues on schedule.

**Integration Pattern:**
```python
from cronpilot import CronExpression
import datetime

queue_schedules = {
    "high_priority": CronExpression("*/1 * * * *"),   # Every minute
    "normal": CronExpression("*/5 * * * *"),           # Every 5 minutes
    "low_priority": CronExpression("*/30 * * * *"),    # Every 30 minutes
    "batch": CronExpression("0 2 * * *"),              # 2 AM daily
}

now = datetime.datetime.now()
for queue_name, cron in queue_schedules.items():
    if cron.matches(now):
        process_queue(queue_name)
```

### With ProfileScope
**Benchmark Scheduling Use Case:** Run performance benchmarks on schedule.

**Integration Pattern:**
```python
from cronpilot import CronExpression

nightly_benchmark = CronExpression("0 3 * * *")
weekly_full_suite = CronExpression("0 2 * * 0")

if nightly_benchmark.matches(now):
    run_quick_benchmarks()
if weekly_full_suite.matches(now):
    run_full_benchmark_suite()
```

---

## 🚀 ADOPTION ROADMAP

### Phase 1: Core Adoption (Week 1)
**Goal:** All agents aware and can use basic features.

**Steps:**
1. Tool deployed to GitHub
2. Quick-start guides sent via Synapse
3. Each agent tests basic workflow (explain, validate, next)
4. Feedback collected

**Success Criteria:**
- All 5 agents have used tool at least once
- No blocking issues reported

### Phase 2: Integration (Week 2-3)
**Goal:** Integrated into daily workflows.

**Steps:**
1. Add CronPilot validation to any tool accepting cron input
2. Use presets in scheduled automation setups
3. Integrate with BCH task runner
4. Monitor usage patterns

**Success Criteria:**
- Used daily by at least 3 agents
- BCH task runner uses CronPilot for validation

### Phase 3: Optimization (Week 4+)
**Goal:** Optimized and fully adopted.

**Steps:**
1. Collect efficiency metrics
2. Implement v1.1 improvements (6-field cron with seconds, timezone support)
3. Create advanced workflow examples
4. Full Team Brain ecosystem integration

**Success Criteria:**
- Measurable time savings
- All cron-related work uses CronPilot
- v1.1 improvements identified

---

## 📊 SUCCESS METRICS

**Adoption Metrics:**
- Number of agents using tool: Target 5/5
- Daily usage count: Track via session logs
- Integration with other tools: Target 5+ integrations

**Efficiency Metrics:**
- Time saved per cron interaction: 10-30 minutes
- Deployment errors prevented: Track cron-related bugs
- Documentation clarity: All schedules have plain-English descriptions

**Quality Metrics:**
- Bug reports: Target 0 critical
- Feature requests: Track for v1.1
- User satisfaction: Qualitative feedback

---

## 🛠️ TECHNICAL INTEGRATION DETAILS

### Import Paths
```python
from cronpilot import CronExpression
from cronpilot import CronBuilder
from cronpilot import validate, get_preset, list_presets
from cronpilot import CronError, CronParseError, CronValidationError
```

### Configuration Integration
**Config File:** Not needed (stateless tool)

**Shared Config with Other Tools:**
```json
{
  "schedules": {
    "health_check": "*/5 * * * *",
    "daily_backup": "0 2 * * *",
    "weekly_report": "0 9 * * 1"
  }
}
```

### Error Handling Integration
**Standardized Exit Codes:**
- 0: Success
- 1: Invalid expression or error

**Exception Hierarchy:**
```
CronError (base)
  CronParseError (malformed expression)
  CronValidationError (out-of-range values)
  CronBuildError (invalid build parameters)
```

### Logging Integration
CronPilot is stateless and does not produce logs. All output goes to stdout/stderr. Capture output in your logging system as needed.

---

## 🔧 MAINTENANCE & SUPPORT

### Update Strategy
- Minor updates (v1.x): Monthly
- Major updates (v2.0+): Quarterly
- Security patches: Immediate (though no external deps minimizes risk)

### Support Channels
- GitHub Issues: Bug reports and feature requests
- Synapse: Team Brain discussions
- Direct to ATLAS: Complex integration questions

### Known Limitations
- No timezone support (UTC assumed, local time used)
- No 6-field cron (seconds not supported in v1.0)
- Maximum 1000 runs per next_runs/previous_runs call
- @reboot is recognized but not schedulable

### Planned Improvements (v1.1)
- Timezone-aware scheduling
- 6-field cron (with seconds)
- Natural language input ("every Monday at 9 AM")
- Crontab file parser (read/write system crontab)

---

## 📚 ADDITIONAL RESOURCES

- Main Documentation: [README.md](README.md)
- Examples: [EXAMPLES.md](EXAMPLES.md)
- Quick Start Guides: [QUICK_START_GUIDES.md](QUICK_START_GUIDES.md)
- Integration Examples: [INTEGRATION_EXAMPLES.md](INTEGRATION_EXAMPLES.md)
- Cheat Sheet: [CHEAT_SHEET.txt](CHEAT_SHEET.txt)
- GitHub: [https://github.com/DonkRonk17/CronPilot](https://github.com/DonkRonk17/CronPilot)

---

**Last Updated:** February 22, 2026
**Maintained By:** ATLAS (Team Brain)
