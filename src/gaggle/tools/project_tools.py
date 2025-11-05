"""Project management tools for Gaggle agents."""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class BaseTool(ABC):
    """Base class for all Gaggle tools."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass


class BacklogTool(BaseTool):
    """Tool for managing product backlog."""
    
    def __init__(self):
        super().__init__("backlog_tool")
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute backlog operations."""
        if action == "prioritize":
            return await self.prioritize_stories(kwargs.get("stories", []))
        elif action == "estimate":
            return await self.estimate_story_points(kwargs.get("story", {}))
        elif action == "validate":
            return await self.validate_story(kwargs.get("story", {}))
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def prioritize_stories(self, stories: List[Dict]) -> Dict[str, Any]:
        """Prioritize stories in the backlog."""
        # Placeholder implementation
        return {
            "prioritized_stories": stories,
            "rationale": "Prioritized based on business value and dependencies"
        }
    
    async def estimate_story_points(self, story: Dict) -> Dict[str, Any]:
        """Estimate story points for a story."""
        # Simple estimation based on complexity keywords
        description = story.get("description", "").lower()
        
        if any(word in description for word in ["complex", "integration", "architecture"]):
            points = 8
        elif any(word in description for word in ["api", "database", "security"]):
            points = 5
        elif any(word in description for word in ["ui", "form", "validation"]):
            points = 3
        else:
            points = 2
        
        return {
            "estimated_points": points,
            "confidence": "medium",
            "rationale": f"Based on complexity indicators in story description"
        }
    
    async def validate_story(self, story: Dict) -> Dict[str, Any]:
        """Validate a user story for completeness."""
        issues = []
        
        if not story.get("title"):
            issues.append("Missing story title")
        
        description = story.get("description", "")
        if not any(phrase in description.lower() for phrase in ["as a", "i want", "so that"]):
            issues.append("Story doesn't follow standard format")
        
        if not story.get("acceptance_criteria"):
            issues.append("Missing acceptance criteria")
        
        if not story.get("story_points") or story.get("story_points") <= 0:
            issues.append("Missing or invalid story points")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "suggestions": self._get_improvement_suggestions(issues)
        }
    
    def _get_improvement_suggestions(self, issues: List[str]) -> List[str]:
        """Get suggestions for improving the story."""
        suggestions = []
        
        for issue in issues:
            if "format" in issue:
                suggestions.append("Use 'As a [user], I want [goal] so that [benefit]' format")
            elif "acceptance criteria" in issue:
                suggestions.append("Add 3-5 specific, testable acceptance criteria")
            elif "story points" in issue:
                suggestions.append("Estimate complexity using planning poker (1,2,3,5,8,13)")
        
        return suggestions


class StoryTemplateTool(BaseTool):
    """Tool for creating user story templates."""
    
    def __init__(self):
        super().__init__("story_template_tool")
    
    async def execute(self, template_type: str = "standard", **kwargs) -> Dict[str, Any]:
        """Generate a user story template."""
        templates = {
            "standard": self._standard_template(),
            "epic": self._epic_template(),
            "technical": self._technical_template(),
            "bug": self._bug_template()
        }
        
        template = templates.get(template_type, templates["standard"])
        
        return {
            "template": template,
            "template_type": template_type,
            "guidelines": self._get_template_guidelines(template_type)
        }
    
    def _standard_template(self) -> Dict[str, str]:
        """Standard user story template."""
        return {
            "title": "[Brief descriptive title]",
            "description": "As a [type of user], I want [goal/desire] so that [benefit/value]",
            "acceptance_criteria": [
                "Given [context], when [action], then [outcome]",
                "The feature should [specific requirement]",
                "The user should be able to [capability]"
            ],
            "definition_of_done": [
                "Code is written and reviewed",
                "Unit tests are written and passing",
                "Feature is tested by QA",
                "Documentation is updated"
            ]
        }
    
    def _epic_template(self) -> Dict[str, str]:
        """Epic template for large features."""
        return {
            "title": "[Epic name]",
            "description": "As a [user type], I want [high-level goal] so that [business value]",
            "user_stories": [
                "Break down into 3-8 user stories",
                "Each story should be deliverable within one sprint"
            ],
            "acceptance_criteria": [
                "All user stories are completed",
                "Integration testing is successful",
                "Performance criteria are met"
            ]
        }
    
    def _technical_template(self) -> Dict[str, str]:
        """Technical story template."""
        return {
            "title": "[Technical improvement/task]",
            "description": "As a [developer/system], I need [technical change] so that [technical benefit]",
            "technical_requirements": [
                "[Specific technical requirement]",
                "[Performance/security/maintainability goal]"
            ],
            "acceptance_criteria": [
                "Technical implementation meets requirements",
                "Code is properly tested",
                "Documentation is updated"
            ]
        }
    
    def _bug_template(self) -> Dict[str, str]:
        """Bug fix template."""
        return {
            "title": "Fix: [Brief description of bug]",
            "description": "As a [affected user], the [feature] should [expected behavior] but currently [actual behavior]",
            "reproduction_steps": [
                "Step 1: [action]",
                "Step 2: [action]",
                "Expected: [outcome]",
                "Actual: [outcome]"
            ],
            "acceptance_criteria": [
                "Bug is fixed and no longer reproducible",
                "Regression tests are added",
                "No new bugs are introduced"
            ]
        }
    
    def _get_template_guidelines(self, template_type: str) -> List[str]:
        """Get guidelines for using the template."""
        guidelines = {
            "standard": [
                "Focus on user value and outcomes",
                "Keep stories small and deliverable",
                "Include 3-5 specific acceptance criteria"
            ],
            "epic": [
                "Break down into smaller user stories",
                "Define clear business value",
                "Consider dependencies between stories"
            ],
            "technical": [
                "Justify technical necessity",
                "Include measurable success criteria",
                "Consider impact on other systems"
            ],
            "bug": [
                "Provide clear reproduction steps",
                "Include expected vs actual behavior",
                "Prioritize based on severity"
            ]
        }
        
        return guidelines.get(template_type, guidelines["standard"])


class SprintBoardTool(BaseTool):
    """Tool for managing sprint board."""
    
    def __init__(self):
        super().__init__("sprint_board_tool")
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute sprint board operations."""
        if action == "update_status":
            return await self.update_item_status(kwargs.get("item_id"), kwargs.get("new_status"))
        elif action == "get_board_state":
            return await self.get_board_state(kwargs.get("sprint_id"))
        elif action == "move_item":
            return await self.move_item(kwargs.get("item_id"), kwargs.get("from_column"), kwargs.get("to_column"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def update_item_status(self, item_id: str, new_status: str) -> Dict[str, Any]:
        """Update status of a sprint item."""
        return {
            "item_id": item_id,
            "old_status": "todo",  # Would be fetched from storage
            "new_status": new_status,
            "updated_at": "2024-01-01T12:00:00Z"
        }
    
    async def get_board_state(self, sprint_id: str) -> Dict[str, Any]:
        """Get current state of the sprint board."""
        return {
            "sprint_id": sprint_id,
            "columns": {
                "todo": {"count": 5, "items": []},
                "in_progress": {"count": 3, "items": []},
                "in_review": {"count": 2, "items": []},
                "done": {"count": 8, "items": []}
            },
            "total_items": 18,
            "completion_percentage": 44.4
        }
    
    async def move_item(self, item_id: str, from_column: str, to_column: str) -> Dict[str, Any]:
        """Move item between columns."""
        return {
            "item_id": item_id,
            "from_column": from_column,
            "to_column": to_column,
            "moved_at": "2024-01-01T12:00:00Z"
        }


class MetricsTool(BaseTool):
    """Tool for tracking sprint and team metrics."""
    
    def __init__(self):
        super().__init__("metrics_tool")
    
    async def execute(self, metric_type: str, **kwargs) -> Dict[str, Any]:
        """Execute metrics operations."""
        if metric_type == "velocity":
            return await self.calculate_velocity(kwargs.get("sprint_id"))
        elif metric_type == "burndown":
            return await self.get_burndown_data(kwargs.get("sprint_id"))
        elif metric_type == "team_performance":
            return await self.get_team_performance(kwargs.get("team_id"))
        elif metric_type == "cost_analysis":
            return await self.analyze_costs(kwargs.get("sprint_id"))
        else:
            return {"error": f"Unknown metric type: {metric_type}"}
    
    async def calculate_velocity(self, sprint_id: str) -> Dict[str, Any]:
        """Calculate sprint velocity."""
        return {
            "sprint_id": sprint_id,
            "completed_story_points": 23.0,
            "planned_story_points": 25.0,
            "velocity_percentage": 92.0,
            "trend": "stable",
            "historical_average": 21.5
        }
    
    async def get_burndown_data(self, sprint_id: str) -> Dict[str, Any]:
        """Get burndown chart data."""
        return {
            "sprint_id": sprint_id,
            "total_points": 25.0,
            "remaining_points": 2.0,
            "days_elapsed": 8,
            "days_remaining": 2,
            "burndown_rate": "on_track",
            "daily_data": [
                {"day": 1, "remaining": 25.0},
                {"day": 2, "remaining": 22.0},
                {"day": 3, "remaining": 18.0},
                {"day": 4, "remaining": 15.0},
                {"day": 5, "remaining": 12.0},
                {"day": 6, "remaining": 8.0},
                {"day": 7, "remaining": 5.0},
                {"day": 8, "remaining": 2.0}
            ]
        }
    
    async def get_team_performance(self, team_id: str) -> Dict[str, Any]:
        """Get team performance metrics."""
        return {
            "team_id": team_id,
            "average_velocity": 22.5,
            "completion_rate": 89.2,
            "quality_score": 85.0,
            "collaboration_index": 92.0,
            "improvement_trend": "positive",
            "key_strengths": [
                "Consistent velocity",
                "Good collaboration",
                "High code quality"
            ],
            "areas_for_improvement": [
                "Estimation accuracy",
                "Early testing"
            ]
        }
    
    async def analyze_costs(self, sprint_id: str) -> Dict[str, Any]:
        """Analyze sprint costs."""
        return {
            "sprint_id": sprint_id,
            "total_cost": 245.67,
            "cost_per_story_point": 10.68,
            "cost_breakdown": {
                "coordination": 25.50,
                "development": 180.25,
                "architecture": 35.12,
                "testing": 4.80
            },
            "budget_status": "under_budget",
            "efficiency_score": 88.5
        }


class BlockerTracker(BaseTool):
    """Tool for tracking and managing blockers."""
    
    def __init__(self):
        super().__init__("blocker_tracker")
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute blocker tracking operations."""
        if action == "add_blocker":
            return await self.add_blocker(kwargs.get("blocker_data"))
        elif action == "resolve_blocker":
            return await self.resolve_blocker(kwargs.get("blocker_id"))
        elif action == "get_active_blockers":
            return await self.get_active_blockers(kwargs.get("sprint_id"))
        elif action == "escalate_blocker":
            return await self.escalate_blocker(kwargs.get("blocker_id"))
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def add_blocker(self, blocker_data: Dict) -> Dict[str, Any]:
        """Add a new blocker."""
        blocker_id = f"BLOCK-{hash(str(blocker_data)) % 10000:04d}"
        
        return {
            "blocker_id": blocker_id,
            "title": blocker_data.get("title", "Unknown blocker"),
            "description": blocker_data.get("description", ""),
            "severity": blocker_data.get("severity", "medium"),
            "affected_items": blocker_data.get("affected_items", []),
            "created_at": "2024-01-01T12:00:00Z",
            "status": "active"
        }
    
    async def resolve_blocker(self, blocker_id: str) -> Dict[str, Any]:
        """Resolve a blocker."""
        return {
            "blocker_id": blocker_id,
            "status": "resolved",
            "resolved_at": "2024-01-01T12:00:00Z",
            "resolution": "Blocker resolved through team collaboration"
        }
    
    async def get_active_blockers(self, sprint_id: str) -> Dict[str, Any]:
        """Get all active blockers for a sprint."""
        return {
            "sprint_id": sprint_id,
            "active_blockers": [
                {
                    "blocker_id": "BLOCK-0001",
                    "title": "External API dependency",
                    "severity": "high",
                    "days_active": 2,
                    "affected_items": ["STORY-123", "TASK-456"]
                },
                {
                    "blocker_id": "BLOCK-0002", 
                    "title": "Code review bottleneck",
                    "severity": "medium",
                    "days_active": 1,
                    "affected_items": ["TASK-789"]
                }
            ],
            "total_count": 2,
            "high_severity_count": 1
        }
    
    async def escalate_blocker(self, blocker_id: str) -> Dict[str, Any]:
        """Escalate a blocker to higher priority."""
        return {
            "blocker_id": blocker_id,
            "escalated_at": "2024-01-01T12:00:00Z",
            "new_severity": "critical",
            "escalation_reason": "Blocking multiple sprint items",
            "assigned_resolver": "tech_lead"
        }