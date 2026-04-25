from datetime import datetime, timedelta


def _recent_health_drop(recent_records):
    if not recent_records:
        return 0.0

    latest_slice = recent_records[-5:]
    if len(latest_slice) < 2:
        return 0.0

    first_score = float(latest_slice[0].get("health_score", latest_slice[-1].get("health_score", 0)) or 0)
    last_score = float(latest_slice[-1].get("health_score", first_score) or first_score)
    return max(0.0, first_score - last_score)


def _build_schedule(priority, temp, soc, health_drop):
    now = datetime.utcnow()

    if priority == "Critical":
        return now + timedelta(hours=1), "Immediate dispatch"
    if temp >= 40 or soc <= 20:
        return now + timedelta(hours=6), "Same-day maintenance"
    if priority == "High" or health_drop >= 10:
        return now + timedelta(hours=12), "Next shift inspection"
    if priority == "Medium":
        return now + timedelta(days=1), "24-hour review"
    return now + timedelta(days=3), "Routine monitoring"


def build_maintenance_plan(prediction, telemetry, recent_records=None):
    recent_records = recent_records or []
    voltage = float(telemetry.get("voltage", 0.0) or 0.0)
    current = float(telemetry.get("current", 0.0) or 0.0)
    soc = float(telemetry.get("soc", 0.0) or 0.0)
    temp = float(telemetry.get("temp", 0.0) or 0.0)
    degradation_level = float(telemetry.get("degradation_level", 0.0) or 0.0)
    health_score = float(prediction.get("health_score", 0.0) or 0.0)
    status = prediction.get("status", "Safe")
    health_drop = _recent_health_drop(recent_records)

    if status == "Critical" or temp >= 45 or health_score < 35 or degradation_level >= 45:
        priority = "Critical"
        task_type = "Emergency Inspection"
        action_status = "Dispatched"
        execution_mode = "Auto-dispatch"
        assigned_team = "Emergency EV Maintenance"
        title = "Dispatch urgent battery maintenance"
        summary = "Battery risk crossed the critical threshold, so the agent opened an urgent maintenance workflow."
        actions = [
            "Lock high-load charging and heavy discharge operations.",
            "Dispatch field technician for thermal and cell-balancing inspection.",
            "Validate cooling loop, connectors, and pack insulation before returning to service."
        ]
    elif status == "Warning" or temp >= 40 or soc <= 20 or health_drop >= 10 or degradation_level >= 30:
        priority = "High"
        task_type = "Preventive Maintenance"
        action_status = "Scheduled"
        execution_mode = "Auto-schedule"
        assigned_team = "Predictive Maintenance Team"
        title = "Schedule preventive battery service"
        summary = "Battery performance is drifting from the safe operating band, so the agent scheduled preventive service."
        actions = [
            "Inspect charging profile and rebalance cells if variance is detected.",
            "Review thermal behavior and verify cooling efficiency.",
            "Run a technician health audit before the next heavy-duty cycle."
        ]
    elif health_score < 80 or abs(current) >= 45 or temp >= 35 or degradation_level >= 15:
        priority = "Medium"
        task_type = "Condition Review"
        action_status = "Monitoring"
        execution_mode = "Autonomous review"
        assigned_team = "Operations Monitoring"
        title = "Plan condition-based maintenance review"
        summary = "The agent detected moderate stress indicators and planned a near-term maintenance review."
        actions = [
            "Track the next charging cycle for abnormal current spikes.",
            "Recheck pack temperature and voltage stability in the next review window.",
            "Escalate automatically if health score drops further."
        ]
    else:
        priority = "Low"
        task_type = "Routine Monitoring"
        action_status = "Monitoring"
        execution_mode = "Autonomous monitoring"
        assigned_team = "Operations Monitoring"
        title = "Continue routine battery monitoring"
        summary = "Battery output is within the expected range, so the agent kept the pack on routine monitoring."
        actions = [
            "Keep scheduled telemetry scans active.",
            "Maintain standard charging and discharge profile.",
            "Re-run maintenance planning after the next prediction cycle."
        ]

    scheduled_for, schedule_label = _build_schedule(priority, temp, soc, health_drop)

    automation_notes = (
        f"Agent reviewed voltage {voltage:.1f} V, current {current:.1f} A, SOC {soc:.1f}%, "
        f"temperature {temp:.1f} C, degradation {degradation_level:.1f}%, status {status}, "
        f"and recent health drop {health_drop:.1f} points."
    )

    return {
        "task_type": task_type,
        "priority": priority,
        "title": title,
        "summary": summary,
        "action_status": action_status,
        "execution_mode": execution_mode,
        "assigned_team": assigned_team,
        "scheduled_for": scheduled_for,
        "schedule_label": schedule_label,
        "recommended_actions": actions,
        "automation_notes": automation_notes
    }
