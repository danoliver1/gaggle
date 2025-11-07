"""Sprint metrics dashboard for real-time monitoring and analytics."""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog

from ..models.sprint import SprintModel, SprintStatus
from ..models.task import TaskModel, TaskStatus
from ..models.story import UserStory, StoryStatus
from ..utils.logging import get_logger
from ..integrations.llm_providers import llm_provider_manager


logger = structlog.get_logger(__name__)


@dataclass
class SprintMetrics:
    """Sprint performance metrics."""
    sprint_id: str
    sprint_goal: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    
    # Progress metrics
    total_stories: int
    completed_stories: int
    total_tasks: int
    completed_tasks: int
    progress_percentage: float
    
    # Velocity metrics
    planned_story_points: float
    completed_story_points: float
    velocity: float
    
    # Quality metrics
    bugs_found: int
    bugs_fixed: int
    test_coverage: float
    code_review_score: float
    
    # Team metrics
    team_satisfaction: float
    blocked_tasks: int
    cycle_time_hours: float
    
    # Cost metrics
    total_tokens_used: int
    total_cost: float
    cost_per_story_point: float
    
    # Efficiency metrics
    parallel_execution_rate: float
    automation_coverage: float
    deployment_frequency: int


class SprintMetricsCollector:
    """Collects and aggregates sprint metrics."""
    
    def __init__(self):
        self.logger = get_logger("sprint_metrics_collector")
    
    async def collect_sprint_metrics(self, sprint: SprintModel) -> SprintMetrics:
        """Collect comprehensive metrics for a sprint."""
        
        self.logger.info("collecting_sprint_metrics", sprint_id=sprint.id)
        
        # Progress metrics
        progress_metrics = self._calculate_progress_metrics(sprint)
        
        # Velocity metrics
        velocity_metrics = self._calculate_velocity_metrics(sprint)
        
        # Quality metrics
        quality_metrics = await self._calculate_quality_metrics(sprint)
        
        # Team metrics
        team_metrics = self._calculate_team_metrics(sprint)
        
        # Cost metrics
        cost_metrics = await self._calculate_cost_metrics(sprint)
        
        # Efficiency metrics
        efficiency_metrics = self._calculate_efficiency_metrics(sprint)
        
        metrics = SprintMetrics(
            sprint_id=sprint.id,
            sprint_goal=sprint.goal,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            **progress_metrics,
            **velocity_metrics,
            **quality_metrics,
            **team_metrics,
            **cost_metrics,
            **efficiency_metrics
        )
        
        self.logger.info(
            "sprint_metrics_collected",
            sprint_id=sprint.id,
            progress=metrics.progress_percentage,
            velocity=metrics.velocity,
            cost=metrics.total_cost
        )
        
        return metrics
    
    def _calculate_progress_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate sprint progress metrics."""
        
        total_stories = len(sprint.user_stories)
        completed_stories = len([s for s in sprint.user_stories if s.status == StoryStatus.DONE])
        
        total_tasks = len(sprint.tasks)
        completed_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.DONE])
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_stories": total_stories,
            "completed_stories": completed_stories,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "progress_percentage": progress_percentage
        }
    
    def _calculate_velocity_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate sprint velocity metrics."""
        
        planned_story_points = sum(story.story_points for story in sprint.user_stories)
        completed_story_points = sum(
            story.story_points 
            for story in sprint.user_stories 
            if story.status == StoryStatus.DONE
        )
        
        # Calculate velocity (story points per week)
        if sprint.start_date and sprint.end_date:
            duration_weeks = (sprint.end_date - sprint.start_date).days / 7
            velocity = completed_story_points / max(1, duration_weeks)
        else:
            velocity = completed_story_points / sprint.duration_weeks
        
        return {
            "planned_story_points": planned_story_points,
            "completed_story_points": completed_story_points,
            "velocity": velocity
        }
    
    async def _calculate_quality_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate quality-related metrics."""
        
        # Mock quality metrics calculation
        # In production, this would integrate with testing systems
        
        bugs_found = 0
        bugs_fixed = 0
        test_coverage = 0.0
        code_review_score = 0.0
        
        # Simulate quality data collection
        for task in sprint.tasks:
            if task.status == TaskStatus.DONE:
                # Simulate bugs found/fixed based on task complexity
                if "complex" in task.description.lower():
                    bugs_found += 2
                    bugs_fixed += 1
                elif "simple" in task.description.lower():
                    bugs_found += 0
                    bugs_fixed += 0
                else:
                    bugs_found += 1
                    bugs_fixed += 1
        
        # Calculate average test coverage and code review scores
        completed_tasks = [t for t in sprint.tasks if t.status == TaskStatus.DONE]
        if completed_tasks:
            test_coverage = 85.5  # Mock average
            code_review_score = 8.7  # Mock average score out of 10
        
        return {
            "bugs_found": bugs_found,
            "bugs_fixed": bugs_fixed,
            "test_coverage": test_coverage,
            "code_review_score": code_review_score
        }
    
    def _calculate_team_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate team performance metrics."""
        
        blocked_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.BLOCKED])
        
        # Calculate average cycle time
        completed_tasks = [t for t in sprint.tasks if t.status == TaskStatus.DONE]
        cycle_times = []
        
        for task in completed_tasks:
            if task.started_at and task.completed_at:
                cycle_time = (task.completed_at - task.started_at).total_seconds() / 3600
                cycle_times.append(cycle_time)
        
        cycle_time_hours = sum(cycle_times) / len(cycle_times) if cycle_times else 0
        
        # Mock team satisfaction score
        team_satisfaction = 8.5  # Would be collected from team surveys
        
        return {
            "team_satisfaction": team_satisfaction,
            "blocked_tasks": blocked_tasks,
            "cycle_time_hours": cycle_time_hours
        }
    
    async def _calculate_cost_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate cost-related metrics."""
        
        # Get LLM usage metrics
        llm_metrics = llm_provider_manager.get_all_usage_metrics()
        
        total_tokens_used = llm_metrics.get("total_tokens", 0)
        total_cost = llm_metrics.get("total_cost", 0.0)
        
        # Calculate cost per story point
        completed_story_points = sum(
            story.story_points 
            for story in sprint.user_stories 
            if story.status == StoryStatus.DONE
        )
        
        cost_per_story_point = total_cost / max(1, completed_story_points)
        
        return {
            "total_tokens_used": total_tokens_used,
            "total_cost": total_cost,
            "cost_per_story_point": cost_per_story_point
        }
    
    def _calculate_efficiency_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Calculate efficiency-related metrics."""
        
        # Calculate parallel execution rate
        total_dev_tasks = len([t for t in sprint.tasks if t.task_type.value in ["frontend", "backend", "fullstack"]])
        parallel_tasks = min(3, total_dev_tasks)  # Assuming 3 developers
        parallel_execution_rate = (parallel_tasks / max(1, total_dev_tasks)) * 100
        
        # Calculate automation coverage
        automated_tasks = len([t for t in sprint.tasks if "test" in t.description.lower() or "automation" in t.description.lower()])
        automation_coverage = (automated_tasks / max(1, len(sprint.tasks))) * 100
        
        # Mock deployment frequency
        deployment_frequency = 3  # Number of deployments during sprint
        
        return {
            "parallel_execution_rate": parallel_execution_rate,
            "automation_coverage": automation_coverage,
            "deployment_frequency": deployment_frequency
        }


class SprintDashboard:
    """Real-time sprint dashboard with visualization and alerts."""
    
    def __init__(self):
        self.metrics_collector = SprintMetricsCollector()
        self.logger = get_logger("sprint_dashboard")
        self.alert_thresholds = {
            "progress_behind_schedule": 10.0,  # % behind schedule
            "velocity_below_target": 20.0,     # % below target velocity
            "quality_score_low": 7.0,          # Score below this triggers alert
            "cost_overrun": 150.0,             # % over budget
            "blocked_tasks_high": 3             # Number of blocked tasks
        }
    
    async def generate_dashboard(self, sprint: SprintModel) -> Dict[str, Any]:
        """Generate comprehensive dashboard for sprint."""
        
        self.logger.info("generating_sprint_dashboard", sprint_id=sprint.id)
        
        # Collect current metrics
        metrics = await self.metrics_collector.collect_sprint_metrics(sprint)
        
        # Generate visualizations
        charts = self._generate_charts(metrics)
        
        # Check for alerts
        alerts = self._check_alerts(metrics)
        
        # Generate insights
        insights = await self._generate_insights(metrics)
        
        # Calculate health score
        health_score = self._calculate_health_score(metrics)
        
        dashboard = {
            "sprint_id": sprint.id,
            "sprint_goal": sprint.goal,
            "generated_at": datetime.now().isoformat(),
            "health_score": health_score,
            "metrics": {
                "progress": {
                    "percentage": metrics.progress_percentage,
                    "stories_completed": f"{metrics.completed_stories}/{metrics.total_stories}",
                    "tasks_completed": f"{metrics.completed_tasks}/{metrics.total_tasks}",
                    "velocity": metrics.velocity,
                    "story_points_completed": f"{metrics.completed_story_points}/{metrics.planned_story_points}"
                },
                "quality": {
                    "test_coverage": f"{metrics.test_coverage:.1f}%",
                    "code_review_score": f"{metrics.code_review_score}/10",
                    "bugs_found": metrics.bugs_found,
                    "bugs_fixed": metrics.bugs_fixed,
                    "bug_fix_rate": f"{(metrics.bugs_fixed / max(1, metrics.bugs_found) * 100):.1f}%"
                },
                "team": {
                    "satisfaction": f"{metrics.team_satisfaction}/10",
                    "blocked_tasks": metrics.blocked_tasks,
                    "cycle_time": f"{metrics.cycle_time_hours:.1f} hours",
                    "parallel_execution_rate": f"{metrics.parallel_execution_rate:.1f}%"
                },
                "cost": {
                    "total_cost": f"${metrics.total_cost:.2f}",
                    "cost_per_story_point": f"${metrics.cost_per_story_point:.2f}",
                    "tokens_used": f"{metrics.total_tokens_used:,}",
                    "efficiency": "High" if metrics.cost_per_story_point < 10.0 else "Medium"
                }
            },
            "charts": charts,
            "alerts": alerts,
            "insights": insights,
            "recommendations": self._generate_recommendations(metrics, alerts)
        }
        
        self.logger.info(
            "sprint_dashboard_generated",
            sprint_id=sprint.id,
            health_score=health_score,
            alerts_count=len(alerts)
        )
        
        return dashboard
    
    def _generate_charts(self, metrics: SprintMetrics) -> Dict[str, Any]:
        """Generate chart data for dashboard visualization."""
        
        return {
            "progress_chart": {
                "type": "progress_bar",
                "data": {
                    "progress": metrics.progress_percentage,
                    "target": 100.0,
                    "color": "green" if metrics.progress_percentage >= 80 else "yellow" if metrics.progress_percentage >= 50 else "red"
                }
            },
            "velocity_chart": {
                "type": "bar_chart", 
                "data": {
                    "planned": metrics.planned_story_points,
                    "completed": metrics.completed_story_points,
                    "velocity": metrics.velocity
                }
            },
            "quality_radar": {
                "type": "radar_chart",
                "data": {
                    "test_coverage": metrics.test_coverage,
                    "code_review_score": metrics.code_review_score * 10,  # Scale to 100
                    "team_satisfaction": metrics.team_satisfaction * 10,  # Scale to 100
                    "automation": metrics.automation_coverage
                }
            },
            "cost_trend": {
                "type": "line_chart",
                "data": {
                    "daily_costs": [5.2, 8.1, 12.3, 15.7, 18.9],  # Mock daily cost progression
                    "budget_line": 20.0
                }
            },
            "burndown_chart": {
                "type": "line_chart",
                "data": {
                    "ideal_burndown": [100, 80, 60, 40, 20, 0],
                    "actual_burndown": [100, 85, 70, 50, 30, 15],  # Mock data
                    "days": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]
                }
            }
        }
    
    def _check_alerts(self, metrics: SprintMetrics) -> List[Dict[str, Any]]:
        """Check for alerts based on metric thresholds."""
        
        alerts = []
        
        # Progress alerts
        if metrics.progress_percentage < 70:  # Assuming mid-sprint
            alerts.append({
                "type": "warning",
                "category": "progress",
                "message": f"Sprint progress at {metrics.progress_percentage:.1f}% - may be behind schedule",
                "severity": "medium",
                "action": "Review task assignments and remove blockers"
            })
        
        # Quality alerts
        if metrics.code_review_score < self.alert_thresholds["quality_score_low"]:
            alerts.append({
                "type": "warning",
                "category": "quality",
                "message": f"Code review score ({metrics.code_review_score}/10) below threshold",
                "severity": "high",
                "action": "Focus on code quality improvements"
            })
        
        # Blocked tasks alert
        if metrics.blocked_tasks >= self.alert_thresholds["blocked_tasks_high"]:
            alerts.append({
                "type": "error",
                "category": "blockers",
                "message": f"{metrics.blocked_tasks} tasks are blocked",
                "severity": "high",
                "action": "Immediate blocker resolution required"
            })
        
        # Cost alerts
        if metrics.cost_per_story_point > 15.0:  # Threshold
            alerts.append({
                "type": "warning",
                "category": "cost",
                "message": f"Cost per story point (${metrics.cost_per_story_point:.2f}) is high",
                "severity": "medium",
                "action": "Review cost optimization strategies"
            })
        
        # Team satisfaction alert
        if metrics.team_satisfaction < 7.0:
            alerts.append({
                "type": "info",
                "category": "team",
                "message": f"Team satisfaction ({metrics.team_satisfaction}/10) could be improved",
                "severity": "low",
                "action": "Check team morale and address concerns"
            })
        
        return alerts
    
    async def _generate_insights(self, metrics: SprintMetrics) -> List[str]:
        """Generate AI-powered insights from sprint metrics."""
        
        insights = []
        
        # Velocity insight
        if metrics.velocity > metrics.planned_story_points / max(1, metrics.sprint_id.count('w')):  # Mock calculation
            insights.append(f"🚀 Team velocity ({metrics.velocity:.1f} points/week) is exceeding expectations")
        
        # Quality insight
        if metrics.test_coverage > 90:
            insights.append(f"✅ Excellent test coverage at {metrics.test_coverage:.1f}%")
        
        # Efficiency insight
        if metrics.parallel_execution_rate > 80:
            insights.append(f"⚡ High parallel execution rate ({metrics.parallel_execution_rate:.1f}%) shows good task coordination")
        
        # Cost insight
        if metrics.cost_per_story_point < 5.0:
            insights.append(f"💰 Cost efficiency is excellent at ${metrics.cost_per_story_point:.2f} per story point")
        
        # Team insight
        if metrics.cycle_time_hours < 24:
            insights.append(f"🔄 Fast cycle time ({metrics.cycle_time_hours:.1f} hours) indicates efficient development")
        
        return insights
    
    def _generate_recommendations(self, metrics: SprintMetrics, alerts: List[Dict]) -> List[str]:
        """Generate actionable recommendations."""
        
        recommendations = []
        
        # Based on alerts
        for alert in alerts:
            if alert["category"] == "blockers":
                recommendations.append("Schedule immediate blocker resolution meeting")
            elif alert["category"] == "quality":
                recommendations.append("Implement pair programming for complex tasks")
            elif alert["category"] == "cost":
                recommendations.append("Optimize model usage and implement caching")
        
        # Based on metrics
        if metrics.parallel_execution_rate < 60:
            recommendations.append("Improve task decomposition for better parallelization")
        
        if metrics.automation_coverage < 70:
            recommendations.append("Increase test automation coverage")
        
        if metrics.bugs_found > metrics.bugs_fixed:
            recommendations.append("Allocate more time for bug fixing")
        
        # Positive reinforcements
        if metrics.team_satisfaction > 8.0:
            recommendations.append("Continue current team practices - satisfaction is high")
        
        return recommendations
    
    def _calculate_health_score(self, metrics: SprintMetrics) -> Dict[str, Any]:
        """Calculate overall sprint health score."""
        
        # Weight different aspects
        progress_score = min(100, metrics.progress_percentage)
        quality_score = (metrics.code_review_score / 10) * 100
        team_score = (metrics.team_satisfaction / 10) * 100
        cost_score = max(0, 100 - (metrics.cost_per_story_point - 5) * 10)  # Penalty for high cost
        
        # Penalties
        blocker_penalty = metrics.blocked_tasks * 10
        bug_penalty = max(0, (metrics.bugs_found - metrics.bugs_fixed) * 5)
        
        overall_score = (
            progress_score * 0.3 +
            quality_score * 0.25 +
            team_score * 0.25 +
            cost_score * 0.2
        ) - blocker_penalty - bug_penalty
        
        overall_score = max(0, min(100, overall_score))
        
        # Determine health status
        if overall_score >= 85:
            status = "excellent"
            color = "green"
        elif overall_score >= 70:
            status = "good"
            color = "green"
        elif overall_score >= 55:
            status = "fair"
            color = "yellow"
        elif overall_score >= 40:
            status = "poor"
            color = "orange"
        else:
            status = "critical"
            color = "red"
        
        return {
            "score": overall_score,
            "status": status,
            "color": color,
            "breakdown": {
                "progress": progress_score * 0.3,
                "quality": quality_score * 0.25,
                "team": team_score * 0.25,
                "cost": cost_score * 0.2,
                "penalties": blocker_penalty + bug_penalty
            }
        }