"""Continuous learning and pattern recognition for team improvement."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json
import logging
from collections import defaultdict, Counter
from statistics import mean, stdev

from ...models.core import UserStory, Task, Sprint, AgentRole
from ...models.enums import TaskStatus, TaskPriority
from .adaptive_planning import SprintMetrics, RiskAssessment

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Types of coordination patterns."""
    SUCCESSFUL_HANDOFF = "successful_handoff"
    FAILED_COORDINATION = "failed_coordination"
    EFFECTIVE_BREAKDOWN = "effective_breakdown"
    QUALITY_ISSUE = "quality_issue"
    VELOCITY_SPIKE = "velocity_spike"
    RISK_MITIGATION = "risk_mitigation"


class LearningCategory(Enum):
    """Categories of learning insights."""
    VELOCITY_OPTIMIZATION = "velocity_optimization"
    RISK_PREDICTION = "risk_prediction" 
    TASK_ESTIMATION = "task_estimation"
    AGENT_COLLABORATION = "agent_collaboration"
    QUALITY_IMPROVEMENT = "quality_improvement"


@dataclass
class CoordinationEvent:
    """Individual coordination event for pattern analysis."""
    timestamp: datetime
    event_type: str
    agents_involved: List[AgentRole]
    context: Dict[str, Any]
    outcome: str
    success_score: float  # 0.0 to 1.0
    
    # Related entities
    sprint_id: Optional[str] = None
    story_id: Optional[str] = None  
    task_id: Optional[str] = None


@dataclass
class CoordinationPattern:
    """Recognized pattern in team coordination."""
    pattern_id: str
    pattern_type: PatternType
    description: str
    
    # Pattern characteristics
    typical_agents: List[AgentRole]
    preconditions: Dict[str, Any]
    actions: List[str]
    outcomes: Dict[str, float]
    
    # Learning metrics
    confidence_score: float  # How sure we are this pattern is valid
    success_rate: float      # Historical success rate
    occurrence_count: int    # How often we've seen this
    
    # Actionable insights
    recommendations: List[str]
    triggers: List[str]       # When to apply this pattern
    
    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """Check if pattern applies to current context."""
        for key, expected_value in self.preconditions.items():
            if key not in context or context[key] != expected_value:
                return False
        return True


@dataclass 
class LearningInsight:
    """Actionable insight derived from pattern analysis."""
    insight_id: str
    category: LearningCategory
    title: str
    description: str
    
    # Evidence
    supporting_data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    
    # Recommendations  
    recommended_actions: List[str]
    expected_impact: str
    implementation_effort: str  # low, medium, high
    
    # Lifecycle
    created_date: datetime
    applied_date: Optional[datetime] = None
    validation_results: Optional[Dict[str, Any]] = None


class PatternRecognizer:
    """Recognizes patterns in team coordination and performance."""
    
    def __init__(self, min_pattern_occurrences: int = 3):
        self.min_pattern_occurrences = min_pattern_occurrences
        self.coordination_events: List[CoordinationEvent] = []
        self.recognized_patterns: Dict[str, CoordinationPattern] = {}
        
    def record_event(self, event: CoordinationEvent) -> None:
        """Record a coordination event for analysis."""
        self.coordination_events.append(event)
        logger.debug(f"Recorded coordination event: {event.event_type}")
        
    async def analyze_patterns(self) -> List[CoordinationPattern]:
        """Analyze recorded events to identify patterns."""
        logger.info("Analyzing coordination patterns...")
        
        # Group events by type and context
        event_groups = self._group_events_by_similarity()
        
        new_patterns = []
        for group_key, events in event_groups.items():
            if len(events) >= self.min_pattern_occurrences:
                pattern = await self._extract_pattern(group_key, events)
                if pattern and pattern.confidence_score >= 0.6:
                    self.recognized_patterns[pattern.pattern_id] = pattern
                    new_patterns.append(pattern)
        
        return new_patterns
    
    def _group_events_by_similarity(self) -> Dict[str, List[CoordinationEvent]]:
        """Group similar events together for pattern extraction."""
        groups = defaultdict(list)
        
        for event in self.coordination_events:
            # Create a group key based on event characteristics
            agents_key = "_".join(sorted([role.value for role in event.agents_involved]))
            context_key = "_".join(sorted([f"{k}:{v}" for k, v in event.context.items()]))
            group_key = f"{event.event_type}_{agents_key}_{context_key}"
            
            groups[group_key].append(event)
            
        return dict(groups)
    
    async def _extract_pattern(
        self, 
        group_key: str, 
        events: List[CoordinationEvent]
    ) -> Optional[CoordinationPattern]:
        """Extract a coordination pattern from similar events."""
        if not events:
            return None
            
        # Analyze common characteristics
        event_types = Counter(event.event_type for event in events)
        most_common_type = event_types.most_common(1)[0][0]
        
        # Find typical agents
        agent_counter = Counter()
        for event in events:
            agent_counter.update(event.agents_involved)
        typical_agents = [agent for agent, _ in agent_counter.most_common(3)]
        
        # Calculate success metrics
        success_scores = [event.success_score for event in events]
        avg_success = mean(success_scores) if success_scores else 0.0
        
        # Extract common preconditions
        preconditions = self._extract_preconditions(events)
        
        # Generate recommendations based on pattern
        recommendations = self._generate_recommendations(most_common_type, avg_success, events)
        
        pattern = CoordinationPattern(
            pattern_id=f"pattern_{len(self.recognized_patterns) + 1}",
            pattern_type=self._classify_pattern_type(most_common_type, avg_success),
            description=f"Pattern in {most_common_type} involving {typical_agents}",
            typical_agents=typical_agents,
            preconditions=preconditions,
            actions=[event.outcome for event in events[:3]],  # Sample actions
            outcomes={"success_rate": avg_success},
            confidence_score=min(0.95, len(events) / 10.0),  # Higher confidence with more data
            success_rate=avg_success,
            occurrence_count=len(events),
            recommendations=recommendations,
            triggers=self._extract_triggers(events)
        )
        
        return pattern
    
    def _extract_preconditions(self, events: List[CoordinationEvent]) -> Dict[str, Any]:
        """Extract common preconditions from events."""
        preconditions = {}
        
        # Find context keys that appear in most events
        all_keys = set()
        for event in events:
            all_keys.update(event.context.keys())
            
        for key in all_keys:
            values = [event.context.get(key) for event in events if key in event.context]
            if len(values) >= len(events) * 0.8:  # Present in 80% of events
                most_common_value = Counter(values).most_common(1)
                if most_common_value:
                    preconditions[key] = most_common_value[0][0]
                    
        return preconditions
    
    def _classify_pattern_type(self, event_type: str, success_rate: float) -> PatternType:
        """Classify the type of pattern based on characteristics."""
        if "handoff" in event_type.lower():
            return PatternType.SUCCESSFUL_HANDOFF if success_rate > 0.7 else PatternType.FAILED_COORDINATION
        elif "breakdown" in event_type.lower():
            return PatternType.EFFECTIVE_BREAKDOWN if success_rate > 0.7 else PatternType.FAILED_COORDINATION
        elif "velocity" in event_type.lower() and success_rate > 0.8:
            return PatternType.VELOCITY_SPIKE
        elif "quality" in event_type.lower():
            return PatternType.QUALITY_ISSUE if success_rate < 0.5 else PatternType.SUCCESSFUL_HANDOFF
        else:
            return PatternType.SUCCESSFUL_HANDOFF if success_rate > 0.7 else PatternType.FAILED_COORDINATION
    
    def _generate_recommendations(
        self, 
        event_type: str, 
        success_rate: float, 
        events: List[CoordinationEvent]
    ) -> List[str]:
        """Generate actionable recommendations based on pattern analysis."""
        recommendations = []
        
        if success_rate > 0.8:
            recommendations.append(f"Continue using successful {event_type} approach")
            recommendations.append("Consider applying this pattern to similar contexts")
        elif success_rate < 0.5:
            recommendations.append(f"Investigate failures in {event_type} process")
            recommendations.append("Add additional coordination checkpoints")
        else:
            recommendations.append(f"Monitor {event_type} process for improvements")
            
        # Add agent-specific recommendations
        agent_performance = defaultdict(list)
        for event in events:
            for agent in event.agents_involved:
                agent_performance[agent].append(event.success_score)
                
        for agent, scores in agent_performance.items():
            avg_score = mean(scores)
            if avg_score < 0.6:
                recommendations.append(f"Provide additional support for {agent.value} in {event_type}")
                
        return recommendations
    
    def _extract_triggers(self, events: List[CoordinationEvent]) -> List[str]:
        """Extract common triggers that lead to this pattern."""
        triggers = []
        
        # Look for common context patterns that trigger this coordination
        context_patterns = defaultdict(int)
        for event in events:
            for key, value in event.context.items():
                pattern = f"{key}={value}"
                context_patterns[pattern] += 1
                
        # Include triggers that appear in at least 50% of events
        threshold = len(events) * 0.5
        for pattern, count in context_patterns.items():
            if count >= threshold:
                triggers.append(pattern)
                
        return triggers[:5]  # Limit to top 5 triggers


class PerformanceTracker:
    """Tracks agent and team performance over time."""
    
    def __init__(self):
        self.agent_metrics: Dict[AgentRole, List[Dict]] = defaultdict(list)
        self.team_metrics: List[Dict] = []
        
    def record_agent_performance(
        self, 
        agent: AgentRole, 
        sprint_id: str, 
        metrics: Dict[str, float]
    ) -> None:
        """Record performance metrics for an agent."""
        performance_record = {
            'sprint_id': sprint_id,
            'timestamp': datetime.now(),
            'metrics': metrics
        }
        self.agent_metrics[agent].append(performance_record)
        
    def record_team_performance(self, sprint_metrics: SprintMetrics) -> None:
        """Record overall team performance."""
        team_record = {
            'sprint_id': sprint_metrics.sprint_id,
            'timestamp': datetime.now(),
            'velocity': sprint_metrics.velocity(),
            'success_rate': sprint_metrics.success_rate(),
            'coordination_failures': sprint_metrics.coordination_failures,
            'quality_metrics': {
                'bugs_introduced': sprint_metrics.bugs_introduced,
                'review_cycles': sprint_metrics.review_cycles,
                'test_coverage': sprint_metrics.test_coverage
            }
        }
        self.team_metrics.append(team_record)
        
    def get_agent_trends(self, agent: AgentRole, lookback_sprints: int = 5) -> Dict[str, Any]:
        """Get performance trends for an agent."""
        recent_records = self.agent_metrics[agent][-lookback_sprints:]
        
        if len(recent_records) < 2:
            return {'trend': 'insufficient_data'}
            
        # Calculate trends for each metric
        trends = {}
        all_metrics = set()
        for record in recent_records:
            all_metrics.update(record['metrics'].keys())
            
        for metric in all_metrics:
            values = [
                record['metrics'].get(metric, 0) 
                for record in recent_records
                if metric in record['metrics']
            ]
            
            if len(values) >= 2:
                recent_avg = mean(values[-2:])
                older_avg = mean(values[:-2]) if len(values) > 2 else values[0]
                
                if recent_avg > older_avg * 1.1:
                    trends[metric] = 'improving'
                elif recent_avg < older_avg * 0.9:
                    trends[metric] = 'declining'
                else:
                    trends[metric] = 'stable'
                    
        return {
            'trend': 'improving' if sum(1 for t in trends.values() if t == 'improving') > len(trends) / 2 else 'stable',
            'metric_trends': trends,
            'sample_size': len(recent_records)
        }
        
    def get_team_performance_summary(self, lookback_sprints: int = 6) -> Dict[str, Any]:
        """Get team performance summary."""
        recent_records = self.team_metrics[-lookback_sprints:]
        
        if not recent_records:
            return {'status': 'no_data'}
            
        velocities = [record['velocity'] for record in recent_records]
        success_rates = [record['success_rate'] for record in recent_records]
        
        return {
            'average_velocity': mean(velocities) if velocities else 0.0,
            'velocity_stability': stdev(velocities) if len(velocities) > 1 else 0.0,
            'average_success_rate': mean(success_rates) if success_rates else 0.0,
            'trend_velocity': self._calculate_trend(velocities),
            'trend_success': self._calculate_trend(success_rates),
            'sprints_analyzed': len(recent_records)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a list of values."""
        if len(values) < 2:
            return 'insufficient_data'
            
        recent_avg = mean(values[-2:])
        older_avg = mean(values[:-2]) if len(values) > 2 else values[0]
        
        if recent_avg > older_avg * 1.1:
            return 'improving'
        elif recent_avg < older_avg * 0.9:
            return 'declining'
        else:
            return 'stable'


class RetrospectiveAnalyzer:
    """Analyzes retrospective data to generate actionable insights."""
    
    def __init__(self):
        self.retrospective_data: List[Dict] = []
        
    def add_retrospective_data(self, sprint_id: str, data: Dict) -> None:
        """Add retrospective data for analysis."""
        retrospective_record = {
            'sprint_id': sprint_id,
            'timestamp': datetime.now(),
            'data': data
        }
        self.retrospective_data.append(retrospective_record)
        
    async def generate_insights(self, lookback_sprints: int = 3) -> List[LearningInsight]:
        """Generate insights from retrospective analysis."""
        recent_retrospectives = self.retrospective_data[-lookback_sprints:]
        insights = []
        
        # Analyze recurring themes
        recurring_issues = self._find_recurring_issues(recent_retrospectives)
        for issue, frequency in recurring_issues.items():
            if frequency >= 2:  # Appeared in 2+ retrospectives
                insight = LearningInsight(
                    insight_id=f"recurring_issue_{len(insights) + 1}",
                    category=LearningCategory.AGENT_COLLABORATION,
                    title=f"Recurring Issue: {issue}",
                    description=f"Issue '{issue}' has appeared in {frequency} recent retrospectives",
                    supporting_data={'frequency': frequency, 'sprints': lookback_sprints},
                    confidence=min(0.9, frequency / lookback_sprints),
                    recommended_actions=[
                        f"Address root cause of {issue}",
                        "Create specific action items to prevent recurrence"
                    ],
                    expected_impact="Reduced coordination failures",
                    implementation_effort="medium",
                    created_date=datetime.now()
                )
                insights.append(insight)
        
        # Analyze improvement opportunities
        improvements = self._identify_improvements(recent_retrospectives)
        for improvement in improvements:
            insight = LearningInsight(
                insight_id=f"improvement_opp_{len(insights) + 1}",
                category=LearningCategory.VELOCITY_OPTIMIZATION,
                title=improvement['title'],
                description=improvement['description'],
                supporting_data=improvement['data'],
                confidence=improvement['confidence'],
                recommended_actions=improvement['actions'],
                expected_impact=improvement['impact'],
                implementation_effort=improvement['effort'],
                created_date=datetime.now()
            )
            insights.append(insight)
            
        return insights
    
    def _find_recurring_issues(self, retrospectives: List[Dict]) -> Dict[str, int]:
        """Find issues that appear in multiple retrospectives."""
        issue_counts = defaultdict(int)
        
        for retro in retrospectives:
            data = retro.get('data', {})
            issues = data.get('what_went_wrong', [])
            blockers = data.get('blockers', [])
            
            all_issues = issues + blockers
            for issue in all_issues:
                # Normalize issue text for comparison
                normalized = issue.lower().strip()
                issue_counts[normalized] += 1
                
        return dict(issue_counts)
    
    def _identify_improvements(self, retrospectives: List[Dict]) -> List[Dict]:
        """Identify improvement opportunities from retrospective data."""
        improvements = []
        
        # Look for positive outcomes that could be amplified
        successful_practices = defaultdict(int)
        for retro in retrospectives:
            data = retro.get('data', {})
            successes = data.get('what_went_well', [])
            
            for success in successes:
                normalized = success.lower().strip()
                successful_practices[normalized] += 1
        
        # Generate improvement suggestions for successful practices
        for practice, frequency in successful_practices.items():
            if frequency >= 2:
                improvements.append({
                    'title': f"Amplify Successful Practice: {practice}",
                    'description': f"Practice '{practice}' contributed to success in {frequency} sprints",
                    'data': {'frequency': frequency, 'practice': practice},
                    'confidence': 0.8,
                    'actions': [
                        f"Standardize the practice: {practice}",
                        "Train team members on this approach",
                        "Monitor adoption and effectiveness"
                    ],
                    'impact': "Increased sprint success rate",
                    'effort': "low"
                })
                
        return improvements


class LearningEngine:
    """Main engine that coordinates continuous learning across all components."""
    
    def __init__(self):
        self.pattern_recognizer = PatternRecognizer()
        self.performance_tracker = PerformanceTracker()
        self.retrospective_analyzer = RetrospectiveAnalyzer()
        self.active_insights: List[LearningInsight] = []
        
    async def process_sprint_completion(
        self, 
        sprint_metrics: SprintMetrics,
        coordination_events: List[CoordinationEvent],
        retrospective_data: Dict
    ) -> List[LearningInsight]:
        """Process completed sprint data to generate learning insights."""
        logger.info(f"Processing sprint completion for learning: {sprint_metrics.sprint_id}")
        
        # Record events and performance
        for event in coordination_events:
            self.pattern_recognizer.record_event(event)
            
        self.performance_tracker.record_team_performance(sprint_metrics)
        
        self.retrospective_analyzer.add_retrospective_data(
            sprint_metrics.sprint_id, 
            retrospective_data
        )
        
        # Generate insights from all sources
        insights = []
        
        # Pattern analysis insights
        patterns = await self.pattern_recognizer.analyze_patterns()
        for pattern in patterns:
            if pattern.confidence_score >= 0.7:
                insight = self._pattern_to_insight(pattern)
                if insight:
                    insights.append(insight)
        
        # Retrospective insights
        retro_insights = await self.retrospective_analyzer.generate_insights()
        insights.extend(retro_insights)
        
        # Performance trend insights
        performance_insights = self._analyze_performance_trends()
        insights.extend(performance_insights)
        
        # Store active insights
        self.active_insights.extend(insights)
        
        return insights
    
    def _pattern_to_insight(self, pattern: CoordinationPattern) -> Optional[LearningInsight]:
        """Convert a coordination pattern to a learning insight."""
        if pattern.pattern_type == PatternType.SUCCESSFUL_HANDOFF:
            return LearningInsight(
                insight_id=f"pattern_insight_{pattern.pattern_id}",
                category=LearningCategory.AGENT_COLLABORATION,
                title="Successful Coordination Pattern Identified",
                description=f"Pattern '{pattern.description}' has {pattern.success_rate:.1%} success rate",
                supporting_data={
                    'pattern_id': pattern.pattern_id,
                    'success_rate': pattern.success_rate,
                    'occurrences': pattern.occurrence_count
                },
                confidence=pattern.confidence_score,
                recommended_actions=pattern.recommendations,
                expected_impact="Improved coordination efficiency",
                implementation_effort="low",
                created_date=datetime.now()
            )
        elif pattern.pattern_type == PatternType.FAILED_COORDINATION:
            return LearningInsight(
                insight_id=f"pattern_insight_{pattern.pattern_id}",
                category=LearningCategory.RISK_PREDICTION,
                title="Coordination Failure Pattern Detected",
                description=f"Pattern '{pattern.description}' leads to coordination failures",
                supporting_data={
                    'pattern_id': pattern.pattern_id,
                    'failure_rate': 1.0 - pattern.success_rate,
                    'occurrences': pattern.occurrence_count
                },
                confidence=pattern.confidence_score,
                recommended_actions=[
                    "Implement additional coordination checkpoints",
                    "Add early warning indicators",
                    "Revise handoff procedures"
                ],
                expected_impact="Reduced coordination failures",
                implementation_effort="medium",
                created_date=datetime.now()
            )
        
        return None
    
    def _analyze_performance_trends(self) -> List[LearningInsight]:
        """Analyze performance trends to generate insights."""
        insights = []
        
        team_summary = self.performance_tracker.get_team_performance_summary()
        
        if team_summary.get('trend_velocity') == 'declining':
            insights.append(LearningInsight(
                insight_id=f"velocity_trend_{datetime.now().isoformat()}",
                category=LearningCategory.VELOCITY_OPTIMIZATION,
                title="Declining Velocity Trend",
                description="Team velocity has been declining in recent sprints",
                supporting_data=team_summary,
                confidence=0.8,
                recommended_actions=[
                    "Analyze velocity decline root causes",
                    "Remove identified blockers",
                    "Consider capacity planning adjustments"
                ],
                expected_impact="Stabilized or improved velocity",
                implementation_effort="medium",
                created_date=datetime.now()
            ))
            
        return insights
    
    def get_actionable_recommendations(self) -> List[Dict[str, Any]]:
        """Get prioritized, actionable recommendations from all insights."""
        recommendations = []
        
        # Sort insights by confidence and impact
        sorted_insights = sorted(
            self.active_insights,
            key=lambda i: (i.confidence, 1 if i.expected_impact else 0),
            reverse=True
        )
        
        for insight in sorted_insights[:5]:  # Top 5 recommendations
            recommendations.append({
                'title': insight.title,
                'category': insight.category.value,
                'confidence': insight.confidence,
                'actions': insight.recommended_actions,
                'effort': insight.implementation_effort,
                'impact': insight.expected_impact
            })
            
        return recommendations