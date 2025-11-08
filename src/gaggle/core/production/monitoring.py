"""Real-time sprint health monitoring and dashboards."""

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ...config.models import AgentRole

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of health metrics."""

    VELOCITY = "velocity"
    QUALITY = "quality"
    COORDINATION = "coordination"
    RISK = "risk"
    AGENT_PERFORMANCE = "agent_performance"
    BURNDOWN = "burndown"
    BLOCKERS = "blockers"
    TECHNICAL_DEBT = "technical_debt"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class HealthStatus(Enum):
    """Overall health status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class HealthMetric:
    """Individual health metric measurement."""

    metric_type: MetricType
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Context
    sprint_id: str | None = None
    agent_role: AgentRole | None = None
    task_id: str | None = None

    # Metadata
    source: str = "system"
    tags: dict[str, str] = field(default_factory=dict)

    def is_stale(self, max_age_minutes: int = 30) -> bool:
        """Check if metric is stale."""
        age = datetime.now() - self.timestamp
        return age.total_seconds() / 60 > max_age_minutes


@dataclass
class MetricThreshold:
    """Threshold configuration for metric alerting."""

    metric_name: str
    warning_threshold: float
    error_threshold: float
    critical_threshold: float

    # Threshold type
    threshold_direction: str = "above"  # above, below, equal

    # Conditions
    consecutive_violations: int = 1
    time_window_minutes: int = 15

    def evaluate(
        self, value: float, recent_values: list[float] = None
    ) -> AlertSeverity:
        """Evaluate threshold against value."""
        if self.threshold_direction == "above":
            if value >= self.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value >= self.error_threshold:
                return AlertSeverity.ERROR
            elif value >= self.warning_threshold:
                return AlertSeverity.WARNING
        elif self.threshold_direction == "below":
            if value <= self.critical_threshold:
                return AlertSeverity.CRITICAL
            elif value <= self.error_threshold:
                return AlertSeverity.ERROR
            elif value <= self.warning_threshold:
                return AlertSeverity.WARNING

        return AlertSeverity.INFO


@dataclass
class Alert:
    """Health alert for sprint issues."""

    alert_id: str
    severity: AlertSeverity
    title: str
    description: str
    metric_name: str

    # Values
    current_value: float
    threshold_value: float

    # Timing
    first_triggered: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # Context
    sprint_id: str | None = None
    agent_role: AgentRole | None = None

    # Status
    acknowledged: bool = False
    resolved: bool = False

    # Actions
    recommended_actions: list[str] = field(default_factory=list)

    def age_minutes(self) -> float:
        """Get alert age in minutes."""
        return (datetime.now() - self.first_triggered).total_seconds() / 60


@dataclass
class AlertRule:
    """Rule for generating alerts from metrics."""

    rule_id: str
    name: str
    description: str
    metric_pattern: str  # Pattern to match metric names

    # Thresholds
    thresholds: list[MetricThreshold]

    # Conditions
    enabled: bool = True
    cooldown_minutes: int = 30

    # Actions
    auto_actions: list[str] = field(default_factory=list)
    notification_channels: list[str] = field(default_factory=list)

    def matches_metric(self, metric: HealthMetric) -> bool:
        """Check if rule applies to metric."""
        if not self.enabled:
            return False

        # Simple pattern matching (in production, use regex or glob)
        return self.metric_pattern in metric.name or metric.name.startswith(
            self.metric_pattern
        )


@dataclass
class Dashboard:
    """Configuration for a monitoring dashboard."""

    dashboard_id: str
    name: str
    description: str

    # Layout
    panels: list[dict[str, Any]] = field(default_factory=list)
    refresh_interval_seconds: int = 30

    # Filters
    sprint_filter: str | None = None
    time_range_hours: int = 24

    # Access
    viewers: list[str] = field(default_factory=list)

    def add_panel(
        self, panel_type: str, title: str, metric_queries: list[str], **kwargs
    ) -> None:
        """Add a panel to the dashboard."""
        panel = {
            "panel_type": panel_type,
            "title": title,
            "metric_queries": metric_queries,
            **kwargs,
        }
        self.panels.append(panel)


class SprintHealthMonitor:
    """Real-time monitoring of sprint health and performance."""

    def __init__(self, max_metrics_per_type: int = 1000):
        self.max_metrics_per_type = max_metrics_per_type

        # Metric storage (in production, use time-series database)
        self.metrics: dict[MetricType, deque] = {
            metric_type: deque(maxlen=max_metrics_per_type)
            for metric_type in MetricType
        }

        # Alerting
        self.alert_rules: dict[str, AlertRule] = {}
        self.active_alerts: dict[str, Alert] = {}
        self.alert_history: list[Alert] = []

        # Dashboards
        self.dashboards: dict[str, Dashboard] = {}

        # Configuration
        self._configure_default_thresholds()
        self._configure_default_rules()
        self._configure_default_dashboards()

    def _configure_default_thresholds(self) -> None:
        """Configure default metric thresholds."""
        self.default_thresholds = {
            "velocity_trend": MetricThreshold(
                metric_name="velocity_trend",
                warning_threshold=-10.0,  # 10% decline
                error_threshold=-20.0,  # 20% decline
                critical_threshold=-30.0,  # 30% decline
                threshold_direction="below",
            ),
            "coordination_failures": MetricThreshold(
                metric_name="coordination_failures",
                warning_threshold=3.0,
                error_threshold=5.0,
                critical_threshold=8.0,
                threshold_direction="above",
            ),
            "blocked_tasks": MetricThreshold(
                metric_name="blocked_tasks",
                warning_threshold=2.0,
                error_threshold=4.0,
                critical_threshold=6.0,
                threshold_direction="above",
            ),
            "test_coverage": MetricThreshold(
                metric_name="test_coverage",
                warning_threshold=75.0,
                error_threshold=70.0,
                critical_threshold=60.0,
                threshold_direction="below",
            ),
            "agent_utilization": MetricThreshold(
                metric_name="agent_utilization",
                warning_threshold=90.0,
                error_threshold=95.0,
                critical_threshold=98.0,
                threshold_direction="above",
            ),
        }

    def _configure_default_rules(self) -> None:
        """Configure default alert rules."""
        # Velocity decline rule
        velocity_rule = AlertRule(
            rule_id="velocity_decline",
            name="Velocity Decline Alert",
            description="Alert when sprint velocity declines significantly",
            metric_pattern="velocity",
            thresholds=[self.default_thresholds["velocity_trend"]],
            notification_channels=["slack", "email"],
        )
        self.alert_rules[velocity_rule.rule_id] = velocity_rule

        # Coordination failure rule
        coordination_rule = AlertRule(
            rule_id="coordination_failures",
            name="Coordination Failure Alert",
            description="Alert when coordination failures exceed threshold",
            metric_pattern="coordination",
            thresholds=[self.default_thresholds["coordination_failures"]],
            auto_actions=["escalate_to_scrum_master"],
            notification_channels=["slack"],
        )
        self.alert_rules[coordination_rule.rule_id] = coordination_rule

        # Quality degradation rule
        quality_rule = AlertRule(
            rule_id="quality_degradation",
            name="Quality Degradation Alert",
            description="Alert when code quality metrics decline",
            metric_pattern="quality",
            thresholds=[self.default_thresholds["test_coverage"]],
            auto_actions=["trigger_quality_review"],
            notification_channels=["slack", "email"],
        )
        self.alert_rules[quality_rule.rule_id] = quality_rule

    def _configure_default_dashboards(self) -> None:
        """Configure default monitoring dashboards."""
        # Sprint Overview Dashboard
        overview_dashboard = Dashboard(
            dashboard_id="sprint_overview",
            name="Sprint Overview",
            description="High-level sprint health and progress",
            refresh_interval_seconds=30,
            time_range_hours=24,
        )

        overview_dashboard.add_panel(
            panel_type="gauge",
            title="Sprint Progress",
            metric_queries=["burndown_progress"],
            min_value=0,
            max_value=100,
        )

        overview_dashboard.add_panel(
            panel_type="line_chart",
            title="Velocity Trend",
            metric_queries=["velocity_daily", "velocity_target"],
            time_range_hours=168,  # 1 week
        )

        overview_dashboard.add_panel(
            panel_type="stat",
            title="Active Blockers",
            metric_queries=["blocked_tasks_count"],
        )

        self.dashboards[overview_dashboard.dashboard_id] = overview_dashboard

        # Agent Performance Dashboard
        agent_dashboard = Dashboard(
            dashboard_id="agent_performance",
            name="Agent Performance",
            description="Individual agent performance and utilization",
            refresh_interval_seconds=60,
        )

        agent_dashboard.add_panel(
            panel_type="bar_chart",
            title="Agent Utilization",
            metric_queries=["agent_utilization_*"],
            groupby="agent_role",
        )

        agent_dashboard.add_panel(
            panel_type="heatmap",
            title="Coordination Matrix",
            metric_queries=["coordination_success_rate"],
            dimensions=["from_agent", "to_agent"],
        )

        self.dashboards[agent_dashboard.dashboard_id] = agent_dashboard

    def record_metric(self, metric: HealthMetric) -> None:
        """Record a health metric."""
        self.metrics[metric.metric_type].append(metric)

        # Evaluate alerts
        asyncio.create_task(self._evaluate_alerts(metric))

        logger.debug(f"Recorded metric: {metric.name} = {metric.value} {metric.unit}")

    async def _evaluate_alerts(self, metric: HealthMetric) -> None:
        """Evaluate alert rules against new metric."""
        for rule in self.alert_rules.values():
            if rule.matches_metric(metric):
                await self._check_rule_thresholds(rule, metric)

    async def _check_rule_thresholds(
        self, rule: AlertRule, metric: HealthMetric
    ) -> None:
        """Check if metric violates rule thresholds."""
        for threshold in rule.thresholds:
            if threshold.metric_name in metric.name:
                severity = threshold.evaluate(metric.value)

                if severity in [
                    AlertSeverity.WARNING,
                    AlertSeverity.ERROR,
                    AlertSeverity.CRITICAL,
                ]:
                    await self._trigger_alert(rule, metric, threshold, severity)

    async def _trigger_alert(
        self,
        rule: AlertRule,
        metric: HealthMetric,
        threshold: MetricThreshold,
        severity: AlertSeverity,
    ) -> None:
        """Trigger an alert for a rule violation."""
        alert_id = f"{rule.rule_id}_{metric.sprint_id or 'global'}_{metric.timestamp.isoformat()}"

        # Check if alert already exists and is in cooldown
        existing_alert = None
        for alert in self.active_alerts.values():
            if (
                alert.metric_name == metric.name
                and alert.sprint_id == metric.sprint_id
                and not alert.resolved
                and alert.age_minutes() < rule.cooldown_minutes
            ):
                existing_alert = alert
                break

        if existing_alert:
            # Update existing alert
            existing_alert.current_value = metric.value
            existing_alert.last_updated = datetime.now()
            existing_alert.severity = max(
                existing_alert.severity, severity, key=lambda x: x.value
            )
        else:
            # Create new alert
            alert = Alert(
                alert_id=alert_id,
                severity=severity,
                title=f"{rule.name}: {metric.name}",
                description=f"{rule.description}. Current value: {metric.value} {metric.unit}, Threshold: {threshold.warning_threshold}",
                metric_name=metric.name,
                current_value=metric.value,
                threshold_value=threshold.warning_threshold,
                sprint_id=metric.sprint_id,
                agent_role=metric.agent_role,
                recommended_actions=self._generate_alert_actions(
                    rule, metric, severity
                ),
            )

            self.active_alerts[alert_id] = alert
            logger.warning(f"Alert triggered: {alert.title}")

            # Execute auto-actions
            for action in rule.auto_actions:
                await self._execute_auto_action(action, alert)

    def _generate_alert_actions(
        self, rule: AlertRule, metric: HealthMetric, severity: AlertSeverity
    ) -> list[str]:
        """Generate recommended actions for alert."""
        actions = []

        if metric.metric_type == MetricType.VELOCITY:
            actions.extend(
                [
                    "Review sprint backlog for blockers",
                    "Check agent workload distribution",
                    "Consider reducing sprint scope",
                ]
            )
        elif metric.metric_type == MetricType.COORDINATION:
            actions.extend(
                [
                    "Review communication protocols",
                    "Schedule team coordination meeting",
                    "Check agent state machine configurations",
                ]
            )
        elif metric.metric_type == MetricType.QUALITY:
            actions.extend(
                [
                    "Trigger additional code review",
                    "Run comprehensive test suite",
                    "Review quality gate configurations",
                ]
            )

        if severity == AlertSeverity.CRITICAL:
            actions.append("Escalate to sprint lead immediately")

        return actions

    async def _execute_auto_action(self, action: str, alert: Alert) -> None:
        """Execute automatic action for alert."""
        logger.info(f"Executing auto-action: {action} for alert: {alert.alert_id}")

        # Mock auto-action execution
        if action == "escalate_to_scrum_master":
            # In production, this would notify the Scrum Master
            pass
        elif action == "trigger_quality_review":
            # In production, this would initiate a quality review process
            pass

        # Add action to alert history
        if not hasattr(alert, "auto_actions_taken"):
            alert.auto_actions_taken = []
        alert.auto_actions_taken.append({"action": action, "timestamp": datetime.now()})

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.acknowledged = True
            alert.last_updated = datetime.now()
            logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
            return True
        return False

    def resolve_alert(
        self, alert_id: str, resolved_by: str, resolution_notes: str = ""
    ) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.last_updated = datetime.now()

            # Move to history
            self.alert_history.append(alert)
            del self.active_alerts[alert_id]

            logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
            return True
        return False

    def get_sprint_health(self, sprint_id: str) -> dict[str, Any]:
        """Get overall health status for a sprint."""
        # Collect recent metrics for sprint
        cutoff_time = datetime.now() - timedelta(hours=1)
        sprint_metrics = []

        for _metric_type, metrics_queue in self.metrics.items():
            sprint_metrics.extend(
                [
                    metric
                    for metric in metrics_queue
                    if (
                        metric.sprint_id == sprint_id
                        and metric.timestamp >= cutoff_time
                    )
                ]
            )

        if not sprint_metrics:
            return {
                "sprint_id": sprint_id,
                "health_status": HealthStatus.WARNING.value,
                "message": "No recent metrics available",
                "last_update": None,
            }

        # Calculate health indicators
        active_alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.sprint_id == sprint_id and not alert.resolved
        ]

        critical_alerts = len(
            [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        )
        error_alerts = len(
            [a for a in active_alerts if a.severity == AlertSeverity.ERROR]
        )
        warning_alerts = len(
            [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
        )

        # Determine overall health
        if critical_alerts > 0:
            health_status = HealthStatus.CRITICAL
            message = f"{critical_alerts} critical alert(s) active"
        elif error_alerts > 2:
            health_status = HealthStatus.UNHEALTHY
            message = f"{error_alerts} error alert(s) active"
        elif error_alerts > 0 or warning_alerts > 3:
            health_status = HealthStatus.WARNING
            message = f"{error_alerts} error(s), {warning_alerts} warning(s)"
        else:
            health_status = HealthStatus.HEALTHY
            message = "All systems operational"

        # Calculate key metrics
        velocity_metrics = [
            m for m in sprint_metrics if m.metric_type == MetricType.VELOCITY
        ]
        current_velocity = velocity_metrics[-1].value if velocity_metrics else 0

        quality_metrics = [
            m for m in sprint_metrics if m.metric_type == MetricType.QUALITY
        ]
        avg_quality_score = (
            sum(m.value for m in quality_metrics) / len(quality_metrics)
            if quality_metrics
            else 0
        )

        return {
            "sprint_id": sprint_id,
            "health_status": health_status.value,
            "message": message,
            "last_update": max(m.timestamp for m in sprint_metrics),
            "metrics_summary": {
                "current_velocity": current_velocity,
                "average_quality_score": avg_quality_score,
                "total_metrics_collected": len(sprint_metrics),
                "active_alerts": len(active_alerts),
            },
            "alerts": {
                "critical": critical_alerts,
                "error": error_alerts,
                "warning": warning_alerts,
                "total": len(active_alerts),
            },
        }

    def get_dashboard_data(
        self, dashboard_id: str, time_range_hours: int = None
    ) -> dict[str, Any]:
        """Get data for a monitoring dashboard."""
        if dashboard_id not in self.dashboards:
            return {"error": "Dashboard not found"}

        dashboard = self.dashboards[dashboard_id]
        time_range = time_range_hours or dashboard.time_range_hours
        cutoff_time = datetime.now() - timedelta(hours=time_range)

        # Collect data for each panel
        panel_data = []

        for panel in dashboard.panels:
            panel_metrics = []

            for query in panel["metric_queries"]:
                # Simple query matching (in production, use proper query engine)
                for _metric_type, metrics_queue in self.metrics.items():
                    matching_metrics = [
                        metric
                        for metric in metrics_queue
                        if (
                            query in metric.name
                            or query.replace("*", "") in metric.name
                        )
                        and metric.timestamp >= cutoff_time
                    ]
                    panel_metrics.extend(matching_metrics)

            # Process metrics based on panel type
            processed_data = self._process_panel_data(
                panel["panel_type"], panel_metrics
            )

            panel_data.append(
                {
                    "title": panel["title"],
                    "panel_type": panel["panel_type"],
                    "data": processed_data,
                }
            )

        return {
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
            "last_refresh": datetime.now(),
            "time_range_hours": time_range,
            "panels": panel_data,
        }

    def _process_panel_data(self, panel_type: str, metrics: list[HealthMetric]) -> Any:
        """Process metrics for specific panel type."""
        if not metrics:
            return []

        if panel_type == "line_chart":
            # Time series data
            return [
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "value": metric.value,
                    "metric_name": metric.name,
                }
                for metric in sorted(metrics, key=lambda m: m.timestamp)
            ]
        elif panel_type == "gauge":
            # Latest value
            latest = max(metrics, key=lambda m: m.timestamp)
            return {
                "current_value": latest.value,
                "unit": latest.unit,
                "timestamp": latest.timestamp.isoformat(),
            }
        elif panel_type == "stat":
            # Single statistic
            return {
                "value": metrics[-1].value if metrics else 0,
                "unit": metrics[-1].unit if metrics else "",
                "count": len(metrics),
            }
        elif panel_type == "bar_chart":
            # Grouped data
            grouped = defaultdict(list)
            for metric in metrics:
                group_key = metric.agent_role.value if metric.agent_role else "unknown"
                grouped[group_key].append(metric.value)

            return [
                {
                    "category": group,
                    "value": sum(values) / len(values) if values else 0,
                    "count": len(values),
                }
                for group, values in grouped.items()
            ]
        else:
            # Default: raw data
            return [
                {
                    "metric_name": metric.name,
                    "value": metric.value,
                    "timestamp": metric.timestamp.isoformat(),
                }
                for metric in metrics
            ]

    def get_monitoring_summary(self) -> dict[str, Any]:
        """Get overall monitoring system summary."""
        total_metrics = sum(len(queue) for queue in self.metrics.values())
        active_alert_count = len(self.active_alerts)

        recent_metrics = 0
        cutoff_time = datetime.now() - timedelta(minutes=5)
        for queue in self.metrics.values():
            recent_metrics += len([m for m in queue if m.timestamp >= cutoff_time])

        return {
            "system_status": "operational",
            "total_metrics_stored": total_metrics,
            "recent_metrics_5min": recent_metrics,
            "active_alerts": active_alert_count,
            "alert_rules_configured": len(self.alert_rules),
            "dashboards_available": len(self.dashboards),
            "last_metric_received": max(
                (
                    max(queue, key=lambda m: m.timestamp).timestamp
                    for queue in self.metrics.values()
                    if queue
                ),
                default=None,
            ),
        }
