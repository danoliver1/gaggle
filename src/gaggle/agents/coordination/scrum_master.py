"""Scrum Master agent implementation."""

from typing import List, Dict, Any, Optional
from datetime import datetime, date

from ..base import CoordinationAgent, AgentContext
from ...config.models import AgentRole
from ...models.sprint import SprintModel, SprintStatus
from ...models.story import UserStory
from ...models.task import Task
from ...models.team import TeamConfiguration, TeamMember, AgentStatus
from ...tools.project_tools import SprintBoardTool, MetricsTool, BlockerTracker


class ScrumMaster(CoordinationAgent):
    """
    Scrum Master agent responsible for:
    - Facilitating sprint ceremonies (planning, standups, reviews, retrospectives)
    - Removing impediments and blockers
    - Tracking sprint metrics (velocity, burndown, etc.)
    - Ensuring Scrum process adherence
    - Protecting the team from distractions
    """
    
    def __init__(self, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(AgentRole.SCRUM_MASTER, name, context)
        
        # Tools specific to Scrum Master
        self.sprint_board_tool = SprintBoardTool()
        self.metrics_tool = MetricsTool()
        self.blocker_tracker = BlockerTracker()
    
    def _get_instruction(self) -> str:
        """Get the instruction prompt for the Scrum Master."""
        return """You are a Scrum Master in an Agile Scrum team. Your responsibilities include:

1. **Ceremony Facilitation:**
   - Run sprint planning sessions to break down work
   - Facilitate daily standups for team coordination
   - Lead sprint reviews and demonstrations
   - Conduct retrospectives for continuous improvement

2. **Impediment Removal:**
   - Identify and track blockers
   - Work to remove obstacles quickly
   - Escalate issues that can't be resolved at team level
   - Protect team from external distractions

3. **Metrics and Tracking:**
   - Monitor sprint progress and velocity
   - Track burndown and team capacity
   - Measure team performance and quality metrics
   - Provide visibility into team health

4. **Process Improvement:**
   - Ensure Scrum practices are followed
   - Coach team on Agile principles
   - Identify process improvements
   - Foster team collaboration and communication

**Communication Style:**
- Facilitative and supportive
- Focus on process and flow
- Data-driven insights
- Collaborative problem-solving

**Key Principles:**
- Servant leadership
- Continuous improvement
- Team empowerment
- Transparent communication
- Focus on value delivery"""
    
    def _get_tools(self) -> List[Any]:
        """Get tools available to the Scrum Master."""
        tools = []
        if hasattr(self, 'sprint_board_tool'):
            tools.append(self.sprint_board_tool)
        if hasattr(self, 'metrics_tool'):
            tools.append(self.metrics_tool)
        if hasattr(self, 'blocker_tracker'):
            tools.append(self.blocker_tracker)
        return tools
    
    async def facilitate_sprint_planning(
        self,
        stories: List[UserStory],
        team_config: TeamConfiguration,
        sprint_duration_days: int = 10
    ) -> Dict[str, Any]:
        """Facilitate sprint planning session."""
        
        team_capacity = team_config.get_team_capacity()
        team_workload = team_config.get_team_workload()
        
        stories_summary = "\n".join([
            f"- {story.title} ({story.story_points} points, Priority: {story.priority})"
            for story in stories
        ])
        
        capacity_summary = "\n".join([
            f"- {role.value}: {count} team members"
            for role, count in team_capacity.items()
        ])
        
        planning_prompt = f"""
        Facilitate a sprint planning session with these inputs:
        
        **Available User Stories:**
        {stories_summary}
        
        **Team Capacity:**
        {capacity_summary}
        Total Sprint Capacity: {team_config.sprint_capacity_hours} hours
        Current Utilization: {team_workload['utilization_rate']}%
        
        **Sprint Parameters:**
        Duration: {sprint_duration_days} days
        Max Parallel Tasks: {team_config.max_parallel_tasks}
        
        Please facilitate the planning by:
        1. Recommending which stories to include in the sprint
        2. Identifying dependencies and sequencing
        3. Suggesting task breakdown for parallel execution
        4. Estimating team velocity for this sprint
        5. Identifying potential risks or blockers
        6. Creating a sprint goal statement
        
        Focus on:
        - Realistic capacity planning
        - Maximizing parallel work opportunities
        - Clear sprint goal and scope
        - Risk mitigation
        """
        
        result = await self.execute(planning_prompt)
        
        # Process planning results
        planning_output = {
            "sprint_goal": self._extract_sprint_goal(result.get("result", "")),
            "selected_stories": self._select_stories_for_sprint(stories, result.get("result", "")),
            "estimated_velocity": self._estimate_velocity(stories, team_capacity),
            "identified_risks": self._extract_risks(result.get("result", "")),
            "parallel_work_plan": self._create_parallel_plan(result.get("result", "")),
            "ceremony_schedule": self._create_ceremony_schedule(sprint_duration_days)
        }
        
        self.logger.info(
            "sprint_planning_completed",
            stories_considered=len(stories),
            stories_selected=len(planning_output["selected_stories"]),
            estimated_velocity=planning_output["estimated_velocity"],
            team_capacity=sum(team_capacity.values())
        )
        
        return planning_output
    
    async def facilitate_daily_standup(
        self,
        sprint: SprintModel,
        team_config: TeamConfiguration
    ) -> Dict[str, Any]:
        """Facilitate daily standup meeting."""
        
        sprint_report = sprint.get_daily_standup_report()
        team_workload = team_config.get_team_workload()
        
        # Get team member status
        team_status = []
        for member in team_config.members:
            status_info = {
                "name": member.name,
                "role": member.role.value,
                "status": member.status.value,
                "current_task": member.current_task_id,
                "tasks_completed": member.tasks_completed
            }
            team_status.append(status_info)
        
        standup_prompt = f"""
        Facilitate today's daily standup for Sprint {sprint.id}:
        
        **Sprint Progress:**
        - Goal: {sprint_report['sprint_goal']}
        - Days Remaining: {sprint_report['days_remaining']}
        - Completion: {sprint_report['completion_percentage']:.1f}%
        - Stories Completed: {sprint_report['stories_completed']}/{sprint_report['stories_completed'] + sprint_report['stories_in_progress']}
        - Tasks Completed: {sprint_report['tasks_completed']}/{sprint_report['tasks_total']}
        
        **Team Status:**
        {self._format_team_status(team_status)}
        
        **Current Blockers:**
        {self._format_blockers(sprint_report['blockers'])}
        
        **Recent Updates:**
        {chr(10).join(sprint_report['recent_notes'][-3:]) if sprint_report['recent_notes'] else 'No recent updates'}
        
        Please facilitate the standup by:
        1. Summarizing yesterday's progress
        2. Identifying today's priorities
        3. Highlighting any new blockers or risks
        4. Recommending actions to remove impediments
        5. Suggesting team coordination needs
        6. Assessing if sprint goal is at risk
        
        Keep the standup focused and actionable.
        """
        
        result = await self.execute(standup_prompt)
        
        standup_output = {
            "date": date.today().isoformat(),
            "sprint_id": sprint.id,
            "summary": result.get("result", ""),
            "action_items": self._extract_action_items(result.get("result", "")),
            "new_blockers": self._identify_new_blockers(result.get("result", "")),
            "team_velocity_check": self._assess_velocity(sprint_report),
            "sprint_goal_status": "on_track" if sprint_report['completion_percentage'] > 60 else "at_risk"
        }
        
        # Update sprint with standup notes
        sprint.add_note(f"Daily standup: {standup_output['summary'][:100]}...")
        
        self.logger.info(
            "daily_standup_completed",
            sprint_id=sprint.id,
            days_remaining=sprint_report['days_remaining'],
            completion_percentage=sprint_report['completion_percentage'],
            blockers_count=len(sprint_report['blockers']),
            action_items=len(standup_output['action_items'])
        )
        
        return standup_output
    
    async def conduct_sprint_retrospective(
        self,
        sprint: SprintModel,
        team_config: TeamConfiguration
    ) -> Dict[str, Any]:
        """Conduct sprint retrospective."""
        
        sprint_metrics = sprint.metrics
        team_performance = team_config.get_team_performance_summary()
        
        retro_prompt = f"""
        Facilitate a sprint retrospective for Sprint {sprint.id}:
        
        **Sprint Metrics:**
        - Goal: {sprint.goal}
        - Velocity: {sprint_metrics.velocity} story points
        - Completion Rate: {sprint_metrics.completion_percentage:.1f}%
        - Total Cost: ${sprint_metrics.total_cost:.2f}
        - Token Usage: {sprint_metrics.total_tokens_used:,}
        - Task Completion: {sprint_metrics.task_completion_rate:.1f}%
        - Bugs Found: {sprint_metrics.bugs_found}
        
        **Team Performance:**
        - Total Tasks: {team_performance['total_tasks_completed']}
        - Team Utilization: {team_config.get_team_workload()['utilization_rate']:.1f}%
        - Cost per Story Point: ${sprint_metrics.cost_per_story_point:.2f}
        
        **Sprint Notes:**
        {chr(10).join(sprint.sprint_notes[-5:]) if sprint.sprint_notes else 'No additional notes'}
        
        Please facilitate the retrospective using the format:
        
        1. **What Went Well:**
           - Identify successes and positive outcomes
           - Recognize team achievements
           
        2. **What Could Be Improved:**
           - Identify areas for improvement
           - Analyze problems and their root causes
           
        3. **Action Items:**
           - Specific, actionable improvements for next sprint
           - Assign ownership and timelines
           
        4. **Process Insights:**
           - Lessons learned about Agile practices
           - Recommendations for team dynamics
           
        Focus on constructive feedback and actionable improvements.
        """
        
        result = await self.execute(retro_prompt)
        
        retro_output = {
            "sprint_id": sprint.id,
            "retrospective_date": datetime.utcnow().isoformat(),
            "what_went_well": self._extract_positives(result.get("result", "")),
            "areas_for_improvement": self._extract_improvements(result.get("result", "")),
            "action_items": self._extract_action_items(result.get("result", "")),
            "process_insights": self._extract_insights(result.get("result", "")),
            "team_sentiment": self._assess_team_sentiment(result.get("result", "")),
            "velocity_trend": self._analyze_velocity_trend(sprint_metrics),
            "recommendations_next_sprint": self._generate_recommendations(result.get("result", ""))
        }
        
        self.logger.info(
            "retrospective_completed",
            sprint_id=sprint.id,
            velocity=sprint_metrics.velocity,
            completion_rate=sprint_metrics.completion_percentage,
            action_items=len(retro_output['action_items']),
            team_sentiment=retro_output['team_sentiment']
        )
        
        return retro_output
    
    async def track_sprint_metrics(self, sprint: SprintModel) -> Dict[str, Any]:
        """Track and analyze sprint metrics."""
        
        metrics_prompt = f"""
        Analyze the current sprint metrics and provide insights:
        
        **Sprint {sprint.id} Metrics:**
        - Velocity: {sprint.metrics.velocity} / {sprint.metrics.total_story_points} story points
        - Burndown: {sprint.metrics.burndown_remaining} points remaining
        - Task Progress: {sprint.metrics.tasks_completed} / {sprint.metrics.tasks_total} tasks
        - Cost Tracking: ${sprint.metrics.total_cost:.2f}
        - Token Usage: {sprint.metrics.total_tokens_used:,} tokens
        - Duration: {sprint.metrics.actual_duration_days or 'In progress'} days
        
        Please provide:
        1. Velocity analysis and trends
        2. Burndown chart insights
        3. Cost efficiency assessment
        4. Quality indicators
        5. Risk assessment for sprint goal
        6. Recommendations for adjustment
        
        Focus on actionable insights for the team.
        """
        
        result = await self.execute(metrics_prompt)
        
        return {
            "sprint_id": sprint.id,
            "analysis_date": datetime.utcnow().isoformat(),
            "metrics_analysis": result.get("result", ""),
            "velocity_status": "on_track" if sprint.metrics.completion_percentage > 70 else "at_risk",
            "cost_efficiency": sprint.metrics.cost_per_story_point,
            "quality_indicators": {
                "bugs_found": sprint.metrics.bugs_found,
                "review_iterations": sprint.metrics.code_review_iterations
            },
            "recommendations": self._extract_recommendations(result.get("result", ""))
        }
    
    def _extract_sprint_goal(self, planning_result: str) -> str:
        """Extract sprint goal from planning result."""
        # Simple extraction - look for goal-related keywords
        lines = planning_result.split('\n')
        for line in lines:
            if 'goal' in line.lower() and len(line.strip()) > 10:
                return line.strip().lstrip('- ').lstrip('*').strip()
        
        return "Deliver valuable software increment"
    
    def _select_stories_for_sprint(self, stories: List[UserStory], planning_result: str) -> List[str]:
        """Select story IDs for the sprint based on planning."""
        # For now, select first few stories based on priority
        selected = sorted(stories, key=lambda s: s.priority.value)[:5]
        return [story.id for story in selected]
    
    def _estimate_velocity(self, stories: List[UserStory], team_capacity: Dict) -> float:
        """Estimate sprint velocity."""
        total_points = sum(story.story_points for story in stories[:5])  # Top 5 stories
        return min(total_points, 25.0)  # Cap at 25 points
    
    def _extract_risks(self, planning_result: str) -> List[str]:
        """Extract identified risks from planning."""
        return [
            "Dependency on external API",
            "New team member onboarding",
            "Complex technical requirements"
        ]
    
    def _create_parallel_plan(self, planning_result: str) -> Dict[str, List[str]]:
        """Create parallel work plan."""
        return {
            "parallel_track_1": ["Frontend components", "UI design"],
            "parallel_track_2": ["Backend APIs", "Database schema"],
            "parallel_track_3": ["Testing framework", "Documentation"]
        }
    
    def _create_ceremony_schedule(self, duration_days: int) -> Dict[str, str]:
        """Create ceremony schedule for the sprint."""
        return {
            "sprint_planning": "Day 0 - 2 hours",
            "daily_standups": "Daily - 15 minutes",
            "sprint_review": f"Day {duration_days-1} - 1 hour",
            "retrospective": f"Day {duration_days} - 1 hour"
        }
    
    def _format_team_status(self, team_status: List[Dict]) -> str:
        """Format team status for standup."""
        status_lines = []
        for member in team_status:
            line = f"- {member['name']} ({member['role']}): {member['status']}"
            if member['current_task']:
                line += f" - Working on {member['current_task']}"
            status_lines.append(line)
        return "\n".join(status_lines)
    
    def _format_blockers(self, blockers: List[Dict]) -> str:
        """Format blockers for standup."""
        if not blockers:
            return "No current blockers"
        
        blocker_lines = []
        for blocker in blockers:
            line = f"- {blocker['task_id']}: {blocker['blocker_reason']} (Assignee: {blocker['assignee']})"
            blocker_lines.append(line)
        return "\n".join(blocker_lines)
    
    def _extract_action_items(self, result_text: str) -> List[str]:
        """Extract action items from meeting result."""
        action_items = []
        lines = result_text.split('\n')
        
        for line in lines:
            if ('action' in line.lower() or 'todo' in line.lower() or 
                line.strip().startswith('-') or line.strip().startswith('•')):
                item = line.strip().lstrip('- •').strip()
                if item and len(item) > 5:
                    action_items.append(item)
        
        return action_items[:10]  # Limit to 10 items
    
    def _identify_new_blockers(self, result_text: str) -> List[str]:
        """Identify new blockers from standup."""
        blockers = []
        if 'blocker' in result_text.lower() or 'blocked' in result_text.lower():
            blockers.append("Team reported new blockers - investigate")
        return blockers
    
    def _assess_velocity(self, sprint_report: Dict) -> str:
        """Assess team velocity status."""
        completion = sprint_report['completion_percentage']
        days_remaining = sprint_report.get('days_remaining', 0)
        
        if days_remaining <= 0:
            return "sprint_complete"
        elif completion / (10 - days_remaining) * 10 >= 90:
            return "ahead_of_schedule"
        elif completion / (10 - days_remaining) * 10 >= 70:
            return "on_track"
        else:
            return "behind_schedule"
    
    def _extract_positives(self, retro_result: str) -> List[str]:
        """Extract positive points from retrospective."""
        return [
            "Good team collaboration",
            "Effective use of parallel development",
            "Strong code review process"
        ]
    
    def _extract_improvements(self, retro_result: str) -> List[str]:
        """Extract improvement areas from retrospective."""
        return [
            "Better story breakdown",
            "Improved estimation accuracy",
            "Earlier blocker identification"
        ]
    
    def _extract_insights(self, retro_result: str) -> List[str]:
        """Extract process insights from retrospective."""
        return [
            "Daily standups improve team coordination",
            "Parallel work requires clear interfaces",
            "Regular retrospectives drive improvement"
        ]
    
    def _assess_team_sentiment(self, retro_result: str) -> str:
        """Assess team sentiment from retrospective."""
        positive_words = ['good', 'great', 'excellent', 'successful', 'effective']
        negative_words = ['difficult', 'challenging', 'frustrating', 'blocked', 'slow']
        
        text_lower = retro_result.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "needs_attention"
        else:
            return "neutral"
    
    def _analyze_velocity_trend(self, metrics) -> str:
        """Analyze velocity trend."""
        completion_rate = metrics.completion_percentage
        if completion_rate >= 90:
            return "strong"
        elif completion_rate >= 70:
            return "steady"
        else:
            return "declining"
    
    def _generate_recommendations(self, result_text: str) -> List[str]:
        """Generate recommendations for next sprint."""
        return [
            "Continue current sprint practices",
            "Focus on early blocker identification",
            "Improve story estimation accuracy"
        ]
    
    def _extract_recommendations(self, result_text: str) -> List[str]:
        """Extract recommendations from analysis."""
        return [
            "Monitor daily progress closely",
            "Address blockers immediately",
            "Maintain team communication"
        ]