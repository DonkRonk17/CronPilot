# CronPilot - Integration Examples

## 🎯 INTEGRATION PHILOSOPHY

CronPilot is designed to work seamlessly with other Team Brain tools. This document provides **copy-paste-ready code examples** for common integration patterns.

---

## 📚 TABLE OF CONTENTS

1. [Pattern 1: CronPilot + BatchRunner](#pattern-1-cronpilot--batchrunner)
2. [Pattern 2: CronPilot + SynapseLink](#pattern-2-cronpilot--synapselink)
3. [Pattern 3: CronPilot + TaskQueuePro](#pattern-3-cronpilot--taskqueuepro)
4. [Pattern 4: CronPilot + ServiceMonitor](#pattern-4-cronpilot--servicemonitor)
5. [Pattern 5: CronPilot + AgentHeartbeat](#pattern-5-cronpilot--agentheartbeat)
6. [Pattern 6: CronPilot + TaskTimer](#pattern-6-cronpilot--tasktimer)
7. [Pattern 7: CronPilot + ConfigManager](#pattern-7-cronpilot--configmanager)
8. [Pattern 8: CronPilot + SessionReplay](#pattern-8-cronpilot--sessionreplay)
9. [Pattern 9: Multi-Tool Scheduling Workflow](#pattern-9-multi-tool-scheduling-workflow)
10. [Pattern 10: Full Team Brain Scheduled Operations](#pattern-10-full-team-brain-scheduled-operations)

---

## Pattern 1: CronPilot + BatchRunner

**Use Case:** Execute batch pipelines on cron-defined schedules.

**Why:** BatchRunner handles parallel command execution; CronPilot determines WHEN to run.

**Code:**

```python
from cronpilot import CronExpression
import datetime

pipelines = {
    "nightly_backup": {
        "cron": CronExpression("0 2 * * *"),
        "commands": ["backup_db.sh", "backup_files.sh", "cleanup.sh"],
    },
    "hourly_sync": {
        "cron": CronExpression("0 * * * *"),
        "commands": ["sync_repos.sh"],
    },
    "weekly_report": {
        "cron": CronExpression("0 9 * * 1"),
        "commands": ["generate_report.py", "email_report.py"],
    },
}

now = datetime.datetime.now()

for name, pipeline in pipelines.items():
    if pipeline["cron"].matches(now):
        print(f"[OK] Triggering pipeline: {name}")
        print(f"     Schedule: {pipeline['cron'].explain()}")
        # batch_runner.execute(pipeline["commands"])
    else:
        next_run = pipeline["cron"].next_runs(1)[0]
        delta = next_run - now
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        print(f"[--] {name}: next in {hours}h {minutes}m")
```

**Result:** Cron-driven pipeline orchestration with clear scheduling visibility.

---

## Pattern 2: CronPilot + SynapseLink

**Use Case:** Send scheduled team notifications via Synapse.

**Why:** Automated reminders and reports without manual intervention.

**Code:**

```python
from cronpilot import CronExpression
import datetime

notifications = {
    "monday_standup": {
        "cron": CronExpression("0 9 * * 1"),
        "to": "TEAM",
        "subject": "Weekly Standup Reminder",
        "body": "Time for our weekly status update! Share your progress.",
    },
    "friday_recap": {
        "cron": CronExpression("0 16 * * 5"),
        "to": "TEAM",
        "subject": "Weekly Recap",
        "body": "End of week! Please log your accomplishments.",
    },
    "daily_health": {
        "cron": CronExpression("0 8 * * 1-5"),
        "to": "FORGE",
        "subject": "Daily Health Report",
        "body": "Agent health summary attached.",
    },
}

now = datetime.datetime.now()

for name, notif in notifications.items():
    if notif["cron"].matches(now):
        print(f"[OK] Sending: {notif['subject']} to {notif['to']}")
        # quick_send(notif["to"], notif["subject"], notif["body"])
```

**Result:** Automated team communication on precisely defined schedules.

---

## Pattern 3: CronPilot + TaskQueuePro

**Use Case:** Process task queues at different intervals based on priority.

**Why:** High-priority tasks process more frequently; low-priority tasks batch.

**Code:**

```python
from cronpilot import CronExpression
import datetime

queue_schedules = {
    "critical": {
        "cron": CronExpression("* * * * *"),
        "description": "Every minute",
    },
    "high": {
        "cron": CronExpression("*/5 * * * *"),
        "description": "Every 5 minutes",
    },
    "normal": {
        "cron": CronExpression("*/15 * * * *"),
        "description": "Every 15 minutes",
    },
    "low": {
        "cron": CronExpression("0 * * * *"),
        "description": "Every hour",
    },
    "batch": {
        "cron": CronExpression("0 2 * * *"),
        "description": "Nightly at 2 AM",
    },
}

now = datetime.datetime.now()
queues_to_process = []

for priority, config in queue_schedules.items():
    if config["cron"].matches(now):
        queues_to_process.append(priority)

if queues_to_process:
    print(f"Processing queues: {', '.join(queues_to_process)}")
    # for queue in queues_to_process:
    #     task_queue.process(queue)
else:
    print("No queues due for processing")
```

**Result:** Priority-aware task processing with configurable intervals.

---

## Pattern 4: CronPilot + ServiceMonitor

**Use Case:** Schedule health checks at different frequencies per service.

**Why:** Critical services need frequent checks; stable services less often.

**Code:**

```python
from cronpilot import CronExpression
import datetime

services = {
    "bch_websocket": {
        "cron": CronExpression("*/1 * * * *"),
        "url": "ws://localhost:8765",
        "critical": True,
    },
    "api_endpoint": {
        "cron": CronExpression("*/5 * * * *"),
        "url": "http://localhost:8000/health",
        "critical": True,
    },
    "database": {
        "cron": CronExpression("*/15 * * * *"),
        "url": "postgresql://localhost:5432",
        "critical": True,
    },
    "backup_service": {
        "cron": CronExpression("0 * * * *"),
        "url": "http://localhost:9000/status",
        "critical": False,
    },
}

now = datetime.datetime.now()

for name, service in services.items():
    if service["cron"].matches(now):
        print(f"[CHECK] {name} ({service['cron'].explain()})")
        # result = service_monitor.check(service["url"])
        # if not result.healthy and service["critical"]:
        #     alert_team(name, result)
```

**Result:** Tiered health monitoring with cron-based frequency control.

---

## Pattern 5: CronPilot + AgentHeartbeat

**Use Case:** Configure agent check-in schedules and detect missed heartbeats.

**Why:** Know exactly when to expect heartbeats and when they're overdue.

**Code:**

```python
from cronpilot import CronExpression
import datetime

agent_schedules = {
    "FORGE": CronExpression("*/5 * * * *"),
    "ATLAS": CronExpression("*/5 * * * *"),
    "CLIO": CronExpression("*/10 * * * *"),
    "IRIS": CronExpression("*/10 * * * *"),
    "BOLT": CronExpression("*/30 * * * *"),
}

last_heartbeats = {
    "FORGE": datetime.datetime(2026, 2, 22, 3, 50),
    "ATLAS": datetime.datetime(2026, 2, 22, 3, 55),
    "CLIO": datetime.datetime(2026, 2, 22, 3, 40),
    "IRIS": datetime.datetime(2026, 2, 22, 3, 30),
    "BOLT": datetime.datetime(2026, 2, 22, 3, 0),
}

now = datetime.datetime.now()

for agent, schedule in agent_schedules.items():
    expected_runs = schedule.next_runs(1, after=last_heartbeats[agent])
    if expected_runs:
        expected = expected_runs[0]
        if now > expected + datetime.timedelta(minutes=2):
            overdue = (now - expected).seconds // 60
            print(f"[!] {agent}: Heartbeat overdue by {overdue} minutes")
        else:
            print(f"[OK] {agent}: On schedule ({schedule.explain()})")
```

**Result:** Proactive detection of agent communication failures.

---

## Pattern 6: CronPilot + TaskTimer

**Use Case:** Schedule Pomodoro work sessions and breaks.

**Why:** Structured work intervals based on cron-defined schedules.

**Code:**

```python
from cronpilot import CronExpression, CronBuilder
import datetime

work_start = CronExpression("0,25,50 9-17 * * 1-5")
short_break = CronExpression("25,50 9-17 * * 1-5")
long_break = CronExpression("0 10,12,14,16 * * 1-5")

now = datetime.datetime.now()

next_work = work_start.next_runs(1, after=now)[0]
next_short = short_break.next_runs(1, after=now)[0]
next_long = long_break.next_runs(1, after=now)[0]

print(f"Next focus session: {next_work.strftime('%H:%M')}")
print(f"Next short break:   {next_short.strftime('%H:%M')}")
print(f"Next long break:    {next_long.strftime('%H:%M')}")
```

**Result:** Automated productivity scheduling with precise timing.

---

## Pattern 7: CronPilot + ConfigManager

**Use Case:** Store and validate cron schedules in centralized config.

**Why:** All schedules in one place, validated on load.

**Code:**

```python
from cronpilot import validate, CronExpression
import json

config = {
    "schedules": {
        "health_check": "*/5 * * * *",
        "daily_backup": "0 2 * * *",
        "weekly_report": "0 9 * * 1",
        "quarterly_review": "0 9 1 1,4,7,10 *",
    }
}

print("Validating schedule configuration...")
all_valid = True

for name, expr in config["schedules"].items():
    result = validate(expr)
    if result["valid"]:
        cron = CronExpression(expr)
        next_run = cron.next_runs(1)[0]
        print(f"  [OK] {name:20s} {expr:20s} -> {cron.explain()}")
        print(f"       Next: {next_run.strftime('%Y-%m-%d %H:%M')}")
    else:
        print(f"  [X] {name:20s} {expr:20s} -> ERROR: {result['error']}")
        all_valid = False

if all_valid:
    print("\n[OK] All schedules valid!")
else:
    print("\n[X] Configuration has errors - fix before deploying")
```

**Result:** Config validation catches schedule errors before deployment.

---

## Pattern 8: CronPilot + SessionReplay

**Use Case:** Log scheduled task execution for debugging.

**Why:** When a scheduled task fails, replay shows exactly what happened.

**Code:**

```python
from cronpilot import CronExpression
import datetime
import json

class ScheduledTaskLogger:
    def __init__(self):
        self.log = []

    def execute_if_due(self, task_name, cron_expr, callback):
        cron = CronExpression(cron_expr)
        now = datetime.datetime.now()

        entry = {
            "timestamp": now.isoformat(),
            "task": task_name,
            "expression": cron_expr,
            "schedule": cron.explain(),
            "was_due": cron.matches(now),
        }

        if cron.matches(now):
            try:
                result = callback()
                entry["status"] = "success"
                entry["result"] = str(result)
            except Exception as e:
                entry["status"] = "error"
                entry["error"] = str(e)
        else:
            entry["status"] = "skipped"
            next_run = cron.next_runs(1, after=now)[0]
            entry["next_run"] = next_run.isoformat()

        self.log.append(entry)
        return entry

    def export_log(self):
        return json.dumps(self.log, indent=2)

logger = ScheduledTaskLogger()
logger.execute_if_due("backup", "0 2 * * *", lambda: "backup complete")
print(logger.export_log())
```

**Result:** Complete audit trail of scheduled task execution.

---

## Pattern 9: Multi-Tool Scheduling Workflow

**Use Case:** Coordinate multiple tools on a single schedule.

**Why:** Real production scenarios involve multiple tools working in concert.

**Code:**

```python
from cronpilot import CronExpression
import datetime

class ScheduledWorkflow:
    def __init__(self, name, cron_expr):
        self.name = name
        self.cron = CronExpression(cron_expr)
        self.steps = []

    def add_step(self, step_name, callback):
        self.steps.append({"name": step_name, "callback": callback})
        return self

    def should_run(self, dt=None):
        if dt is None:
            dt = datetime.datetime.now()
        return self.cron.matches(dt)

    def execute(self):
        if not self.should_run():
            return {"status": "not_due", "next": self.cron.next_runs(1)[0].isoformat()}

        results = []
        for step in self.steps:
            try:
                result = step["callback"]()
                results.append({"step": step["name"], "status": "ok", "result": str(result)})
            except Exception as e:
                results.append({"step": step["name"], "status": "error", "error": str(e)})
                break

        return {"status": "completed", "schedule": self.cron.explain(), "results": results}

# Define workflows
nightly_maintenance = (ScheduledWorkflow("Nightly Maintenance", "0 2 * * *")
    .add_step("backup_database", lambda: "DB backed up")
    .add_step("rotate_logs", lambda: "Logs rotated")
    .add_step("cleanup_temp", lambda: "Temp cleaned")
    .add_step("send_report", lambda: "Report sent"))

hourly_health = (ScheduledWorkflow("Hourly Health Check", "0 * * * *")
    .add_step("check_services", lambda: "All services healthy")
    .add_step("check_disk", lambda: "Disk OK: 45% used"))

# Execute
for workflow in [nightly_maintenance, hourly_health]:
    print(f"\n{workflow.name} ({workflow.cron.explain()}):")
    if workflow.should_run():
        result = workflow.execute()
        for r in result["results"]:
            print(f"  [{r['status'].upper()}] {r['step']}: {r.get('result', r.get('error'))}")
    else:
        next_run = workflow.cron.next_runs(1)[0]
        print(f"  Not due. Next: {next_run.strftime('%Y-%m-%d %H:%M')}")
```

**Result:** Structured multi-step workflow execution on cron schedules.

---

## Pattern 10: Full Team Brain Scheduled Operations

**Use Case:** Complete Team Brain daily operations managed by cron.

**Why:** Demonstrates how CronPilot orchestrates the entire team schedule.

**Code:**

```python
from cronpilot import CronExpression, get_preset
import datetime

team_brain_schedule = {
    "agent_wake": {
        "cron": CronExpression("0 8 * * 1-5"),
        "action": "Wake all agents via TeamBrainOrchestrator",
        "owner": "Logan",
    },
    "morning_standup": {
        "cron": CronExpression("0 9 * * 1-5"),
        "action": "Post standup reminder via SynapseLink",
        "owner": "FORGE",
    },
    "health_monitoring": {
        "cron": CronExpression(get_preset("every_5_minutes")["expression"]),
        "action": "AgentHeartbeat check-in",
        "owner": "ALL",
    },
    "task_queue_process": {
        "cron": CronExpression("*/15 9-17 * * 1-5"),
        "action": "Process TaskQueuePro during business hours",
        "owner": "ATLAS",
    },
    "nightly_backup": {
        "cron": CronExpression("0 2 * * *"),
        "action": "QuickBackup full system backup",
        "owner": "CLIO",
    },
    "weekly_report": {
        "cron": CronExpression("0 16 * * 5"),
        "action": "Generate and distribute weekly report",
        "owner": "FORGE",
    },
    "monthly_review": {
        "cron": CronExpression("0 10 1 * *"),
        "action": "Monthly tool review and maintenance planning",
        "owner": "FORGE",
    },
}

now = datetime.datetime.now()
print(f"Team Brain Schedule Status ({now.strftime('%Y-%m-%d %H:%M')})")
print("=" * 70)

for name, task in team_brain_schedule.items():
    is_due = task["cron"].matches(now)
    next_run = task["cron"].next_runs(1, after=now)[0]

    status = "[DUE NOW]" if is_due else f"[Next: {next_run.strftime('%m/%d %H:%M')}]"
    print(f"  {status:24s} {name:24s} ({task['owner']})")
    print(f"  {'':24s} {task['cron'].explain()}")
    print()
```

**Result:** Complete visibility into Team Brain's automated schedule.

---

## 📊 RECOMMENDED INTEGRATION PRIORITY

**Week 1 (Essential):**
1. BatchRunner — Cron-triggered pipelines
2. SynapseLink — Scheduled notifications
3. ServiceMonitor — Health check intervals

**Week 2 (Productivity):**
4. TaskQueuePro — Priority-based processing
5. AgentHeartbeat — Heartbeat scheduling
6. ConfigManager — Centralized schedule config

**Week 3 (Advanced):**
7. TaskTimer — Pomodoro scheduling
8. SessionReplay — Execution audit logging
9. Multi-tool workflows
10. Full Team Brain operations

---

## 🔧 TROUBLESHOOTING INTEGRATIONS

**Import Errors:**
```python
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "OneDrive/Documents/AutoProjects/CronPilot"))
from cronpilot import CronExpression
```

**Schedule Not Firing:**
```python
from cronpilot import CronExpression
import datetime

cron = CronExpression("0 9 * * 1-5")
now = datetime.datetime.now()

print(f"Current time: {now}")
print(f"Matches: {cron.matches(now)}")
print(f"Next run: {cron.next_runs(1, after=now)[0]}")
print(f"Schedule: {cron.explain()}")
```

**Timezone Issues:**
CronPilot uses local system time. Ensure all agents use the same timezone or convert before matching.

---

**Last Updated:** February 22, 2026
**Maintained By:** ATLAS (Team Brain)
