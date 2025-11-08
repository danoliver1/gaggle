"""Adaptive sprint planning with dynamic velocity and risk assessment."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from statistics import mean, median

from ...config.models import AgentRole
from ...models import Sprint, Task, TaskStatus, UserStory

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Sprint risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VelocityMetric(Enum):
    """Velocity calculation methods."""

    STORY_POINTS = "story_points"
    TASK_COUNT = "task_count"
    EFFORT_HOURS = "effort_hours"


@dataclass
class SprintMetrics:
    """Comprehensive sprint performance metrics."""

    sprint_id: str
    start_date: datetime
    end_date: datetime | None = None

    # Velocity metrics
    planned_story_points: int = 0
    completed_story_points: int = 0
    planned_tasks: int = 0
    completed_tasks: int = 0

    # Quality metrics
    bugs_introduced: int = 0
    review_cycles: int = 0
    test_coverage: float = 0.0

    # Team metrics
    agent_utilization: dict[AgentRole, float] = field(default_factory=dict)
    coordination_failures: int = 0
    blocked_tasks: int = 0

    # Time metrics
    average_task_completion_time: float = 0.0
    sprint_burndown_variance: float = 0.0

    def velocity(self, metric: VelocityMetric = VelocityMetric.STORY_POINTS) -> float:
        """Calculate velocity based on metric type."""
        if not self.end_date:
            return 0.0

        if metric == VelocityMetric.STORY_POINTS:
            return self.completed_story_points
        elif metric == VelocityMetric.TASK_COUNT:
            return self.completed_tasks
        else:  # EFFORT_HOURS
            sprint_duration = (self.end_date - self.start_date).total_seconds() / 3600
            return sprint_duration if sprint_duration > 0 else 0.0

    def success_rate(self) -> float:
        """Calculate sprint success rate."""
        if self.planned_story_points == 0:
            return 0.0
        return self.completed_story_points / self.planned_story_points


@dataclass
class RiskFactor:
    """Individual risk factor assessment."""

    name: str
    description: str
    level: RiskLevel
    impact_score: float  # 0.0 to 1.0
    probability: float  # 0.0 to 1.0
    mitigation_strategy: str

    @property
    def risk_score(self) -> float:
        """Calculate overall risk score."""
        return self.impact_score * self.probability


@dataclass
class RiskAssessment:
    """Comprehensive sprint risk assessment."""

    sprint_id: str
    assessment_date: datetime
    risk_factors: list[RiskFactor] = field(default_factory=list)

    @property
    def overall_risk_level(self) -> RiskLevel:
        """Calculate overall risk level."""
        if not self.risk_factors:
            return RiskLevel.LOW

        max_risk = max(factor.risk_score for factor in self.risk_factors)

        if max_risk >= 0.8:
            return RiskLevel.CRITICAL
        elif max_risk >= 0.6:
            return RiskLevel.HIGH
        elif max_risk >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @property
    def critical_risks(self) -> list[RiskFactor]:
        """Get critical and high risk factors."""
        return [
            factor
            for factor in self.risk_factors
            if factor.level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        ]


class VelocityTracker:
    """Tracks and predicts team velocity over time."""

    def __init__(self, history_window: int = 6):
        self.history_window = history_window
        self.sprint_history: list[SprintMetrics] = []

    def add_sprint_metrics(self, metrics: SprintMetrics) -> None:
        """Add completed sprint metrics."""
        self.sprint_history.append(metrics)

        # Keep only recent history
        if len(self.sprint_history) > self.history_window:
            self.sprint_history = self.sprint_history[-self.history_window :]

    def predict_velocity(
        self,
        metric: VelocityMetric = VelocityMetric.STORY_POINTS,
        method: str = "moving_average",
    ) -> float:
        """Predict velocity for next sprint."""
        if not self.sprint_history:
            return 0.0

        velocities = [sprint.velocity(metric) for sprint in self.sprint_history]

        if method == "moving_average":
            return mean(velocities) if velocities else 0.0
        elif method == "median":
            return median(velocities) if velocities else 0.0
        elif method == "weighted_recent":
            # Weight recent sprints more heavily
            weights = [i + 1 for i in range(len(velocities))]
            weighted_sum = sum(v * w for v, w in zip(velocities, weights, strict=False))
            weight_total = sum(weights)
            return weighted_sum / weight_total if weight_total > 0 else 0.0
        else:
            return mean(velocities) if velocities else 0.0

    def velocity_trend(self) -> str:
        """Analyze velocity trend over time."""
        if len(self.sprint_history) < 2:
            return "insufficient_data"

        recent_velocities = [sprint.velocity() for sprint in self.sprint_history[-3:]]

        if len(recent_velocities) >= 2:
            recent_avg = mean(recent_velocities)
            older_velocities = [
                sprint.velocity() for sprint in self.sprint_history[:-3]
            ]

            if older_velocities:
                older_avg = mean(older_velocities)
                if recent_avg > older_avg * 1.1:
                    return "improving"
                elif recent_avg < older_avg * 0.9:
                    return "declining"
                else:
                    return "stable"

        return "stable"


class CapacityPlanner:
    """Plans team capacity and workload balancing."""

    def __init__(self):
        self.agent_capacities: dict[AgentRole, float] = {
            AgentRole.PRODUCT_OWNER: 0.3,  # Coordination role
            AgentRole.SCRUM_MASTER: 0.3,  # Coordination role
            AgentRole.TECH_LEAD: 0.8,  # Architecture role
            AgentRole.FRONTEND_DEV: 1.0,  # Implementation role
            AgentRole.BACKEND_DEV: 1.0,  # Implementation role
            AgentRole.FULLSTACK_DEV: 1.0,  # Implementation role
            AgentRole.QA_ENGINEER: 0.8,  # Quality role
        }

    def calculate_available_capacity(
        self, sprint_duration_days: int = 14
    ) -> dict[AgentRole, float]:
        """Calculate available capacity for sprint."""
        # Assume 8 hours per day, account for meetings and overhead
        base_hours = sprint_duration_days * 6  # 6 productive hours per day

        return {
            role: base_hours * capacity_factor
            for role, capacity_factor in self.agent_capacities.items()
        }

    def balance_workload(
        self, tasks: list[Task], sprint_duration_days: int = 14
    ) -> dict[AgentRole, list[Task]]:
        """Balance task assignments across team members."""
        available_capacity = self.calculate_available_capacity(sprint_duration_days)
        assignments: dict[AgentRole, list[Task]] = {role: [] for role in AgentRole}
        capacity_used: dict[AgentRole, float] = dict.fromkeys(AgentRole, 0.0)

        # Sort tasks by priority and effort
        sorted_tasks = sorted(
            tasks,
            key=lambda t: (
                getattr(t.priority, "value", t.priority) if t.priority else 3,
                t.estimated_hours or 0,
            ),
            reverse=True,
        )

        for task in sorted_tasks:
            # Find agent role with lowest utilization that can handle this task
            suitable_roles = self._get_suitable_roles(task)

            best_role = None
            min_utilization = float("inf")

            for role in suitable_roles:
                utilization = capacity_used[role] / available_capacity[role]
                remaining_capacity = available_capacity[role] - capacity_used[role]

                if (
                    remaining_capacity >= (task.estimated_hours or 0)
                    and utilization < min_utilization
                ):
                    best_role = role
                    min_utilization = utilization

            if best_role:
                assignments[best_role].append(task)
                capacity_used[best_role] += task.estimated_hours or 0
            else:
                # Assign to least utilized suitable role even if over capacity
                if suitable_roles:
                    fallback_role = min(
                        suitable_roles,
                        key=lambda r: capacity_used[r] / available_capacity[r],
                    )
                    assignments[fallback_role].append(task)
                    capacity_used[fallback_role] += task.estimated_hours or 0

        return assignments

    def _get_suitable_roles(self, task: Task) -> list[AgentRole]:
        """Get agent roles suitable for a task based on task type."""
        task_type = getattr(task, "task_type", "implementation")

        role_mapping = {
            "frontend": [AgentRole.FRONTEND_DEV, AgentRole.FULLSTACK_DEV],
            "backend": [AgentRole.BACKEND_DEV, AgentRole.FULLSTACK_DEV],
            "fullstack": [
                AgentRole.FULLSTACK_DEV,
                AgentRole.FRONTEND_DEV,
                AgentRole.BACKEND_DEV,
            ],
            "architecture": [AgentRole.TECH_LEAD],
            "testing": [AgentRole.QA_ENGINEER],
            "coordination": [AgentRole.SCRUM_MASTER, AgentRole.PRODUCT_OWNER],
        }

        return role_mapping.get(task_type, [AgentRole.FULLSTACK_DEV])


class AdaptiveSprintPlanner:
    """Main adaptive sprint planning coordinator."""

    def __init__(self):
        self.velocity_tracker = VelocityTracker()
        self.capacity_planner = CapacityPlanner()
        self.risk_assessments: dict[str, RiskAssessment] = {}

    async def plan_sprint(
        self,
        sprint: Sprint,
        backlog_stories: list[UserStory],
        historical_metrics: list[SprintMetrics],
    ) -> dict:
        """Plan sprint adaptively based on team performance and risk assessment."""
        logger.info(f"Starting adaptive planning for sprint {sprint.id}")

        # Update velocity tracking
        for metrics in historical_metrics:
            self.velocity_tracker.add_sprint_metrics(metrics)

        # Predict capacity
        predicted_velocity = self.velocity_tracker.predict_velocity()
        velocity_trend = self.velocity_tracker.velocity_trend()

        # Assess risks
        risk_assessment = await self._assess_sprint_risks(sprint, backlog_stories)
        self.risk_assessments[sprint.id] = risk_assessment

        # Adjust velocity based on risk
        risk_adjusted_velocity = self._adjust_velocity_for_risk(
            predicted_velocity, risk_assessment
        )

        # Select stories for sprint
        selected_stories = self._select_sprint_stories(
            backlog_stories, risk_adjusted_velocity
        )

        # Generate tasks and balance workload
        all_tasks = []
        for story in selected_stories:
            tasks = await self._generate_tasks_for_story(story)
            all_tasks.extend(tasks)

        task_assignments = self.capacity_planner.balance_workload(all_tasks)

        return {
            "selected_stories": selected_stories,
            "task_assignments": task_assignments,
            "predicted_velocity": predicted_velocity,
            "risk_adjusted_velocity": risk_adjusted_velocity,
            "velocity_trend": velocity_trend,
            "risk_assessment": risk_assessment,
            "planning_confidence": self._calculate_confidence(risk_assessment),
        }

    async def _assess_sprint_risks(
        self, sprint: Sprint, stories: list[UserStory]
    ) -> RiskAssessment:
        """Assess risks for the sprint."""
        assessment = RiskAssessment(sprint_id=sprint.id, assessment_date=datetime.now())

        # Technical complexity risk
        complex_stories = [s for s in stories if s.story_points and s.story_points >= 8]
        if complex_stories:
            assessment.risk_factors.append(
                RiskFactor(
                    name="high_complexity",
                    description=f"{len(complex_stories)} high-complexity stories (8+ points)",
                    level=(
                        RiskLevel.MEDIUM
                        if len(complex_stories) <= 2
                        else RiskLevel.HIGH
                    ),
                    impact_score=0.7,
                    probability=0.6 if len(complex_stories) <= 2 else 0.8,
                    mitigation_strategy="Break down complex stories, add extra review cycles",
                )
            )

        # Dependency risk
        external_dependencies = sum(1 for s in stories if s.dependencies)
        if external_dependencies > 0:
            assessment.risk_factors.append(
                RiskFactor(
                    name="external_dependencies",
                    description=f"{external_dependencies} stories with external dependencies",
                    level=RiskLevel.MEDIUM,
                    impact_score=0.8,
                    probability=0.4,
                    mitigation_strategy="Identify and engage stakeholders early",
                )
            )

        # Team capacity risk
        velocity_trend = self.velocity_tracker.velocity_trend()
        if velocity_trend == "declining":
            assessment.risk_factors.append(
                RiskFactor(
                    name="declining_velocity",
                    description="Team velocity declining in recent sprints",
                    level=RiskLevel.MEDIUM,
                    impact_score=0.6,
                    probability=0.7,
                    mitigation_strategy="Focus on removing blockers, reduce scope",
                )
            )

        return assessment

    def _adjust_velocity_for_risk(
        self, base_velocity: float, risk_assessment: RiskAssessment
    ) -> float:
        """Adjust predicted velocity based on risk factors."""
        risk_level = risk_assessment.overall_risk_level

        adjustments = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 0.9,
            RiskLevel.HIGH: 0.8,
            RiskLevel.CRITICAL: 0.7,
        }

        return base_velocity * adjustments[risk_level]

    def _select_sprint_stories(
        self, backlog: list[UserStory], target_velocity: float
    ) -> list[UserStory]:
        """Select stories for sprint based on adjusted velocity."""
        # Sort by priority and business value
        sorted_stories = sorted(
            backlog,
            key=lambda s: (
                getattr(s.priority, "value", s.priority) if s.priority else 3,
                -(s.story_points or 0),
            ),
        )

        selected = []
        total_points = 0.0

        for story in sorted_stories:
            story_points = story.story_points or 0
            if total_points + story_points <= target_velocity:
                selected.append(story)
                total_points += story_points
            elif total_points == 0:  # Always include at least one story
                selected.append(story)
                break

        return selected

    async def _generate_tasks_for_story(self, story: UserStory) -> list[Task]:
        """Generate implementation tasks for a story."""
        # This is a simplified task generation - in reality, this would be more sophisticated
        from ...models.task import TaskType

        base_tasks = [
            Task(
                id=f"{story.id}_analysis",
                title=f"Analyze requirements for {story.title}",
                description=f"Technical analysis for: {story.description}",
                story_id=story.id,
                estimated_hours=max(1, (story.story_points or 3) // 4),
                status=TaskStatus.TODO,
                priority=story.priority,
                task_type=TaskType.ARCHITECTURE,
            ),
            Task(
                id=f"{story.id}_implementation",
                title=f"Implement {story.title}",
                description=f"Core implementation for: {story.description}",
                story_id=story.id,
                estimated_hours=max(2, (story.story_points or 3) // 2),
                status=TaskStatus.TODO,
                priority=story.priority,
                task_type=TaskType.FULLSTACK,
            ),
            Task(
                id=f"{story.id}_testing",
                title=f"Test {story.title}",
                description=f"Testing and validation for: {story.description}",
                story_id=story.id,
                estimated_hours=max(1, (story.story_points or 3) // 4),
                status=TaskStatus.TODO,
                priority=story.priority,
                task_type=TaskType.TESTING,
            ),
        ]

        return base_tasks

    def _calculate_confidence(self, risk_assessment: RiskAssessment) -> float:
        """Calculate planning confidence score."""
        risk_level = risk_assessment.overall_risk_level

        confidence_scores = {
            RiskLevel.LOW: 0.9,
            RiskLevel.MEDIUM: 0.7,
            RiskLevel.HIGH: 0.5,
            RiskLevel.CRITICAL: 0.3,
        }

        return confidence_scores[risk_level]
