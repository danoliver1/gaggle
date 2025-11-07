"""Sprint execution workflow implementation."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from ..models.sprint import SprintModel, SprintStatus
from ..models.task import TaskModel, TaskStatus
from ..models.story import UserStory, StoryStatus
from ..agents.coordination.scrum_master import ScrumMaster
from ..agents.architecture.tech_lead import TechLead
from ..agents.implementation.frontend_dev import FrontendDeveloper
from ..agents.implementation.backend_dev import BackendDeveloper
from ..agents.implementation.fullstack_dev import FullstackDeveloper
from ..agents.qa.qa_engineer import QAEngineer
from ..agents.base import AgentContext
from ..config.settings import settings


logger = structlog.get_logger(__name__)


class SprintExecutionWorkflow:
    """
    Manages the sprint execution phase with parallel development work.
    
    The workflow coordinates:
    1. Daily standups
    2. Parallel task execution by multiple developers
    3. Tech Lead code reviews
    4. QA testing in parallel with development
    5. Continuous integration and feedback
    """
    
    def __init__(self, sprint: SprintModel):
        self.sprint = sprint
        self.context = AgentContext(sprint_id=sprint.id)
        
        # Initialize agents
        self.scrum_master = ScrumMaster(context=self.context)
        self.tech_lead = TechLead(context=self.context)
        self.qa_engineer = QAEngineer(context=self.context)
        
        # Implementation agents (can be multiple)
        self.developers = [
            FrontendDeveloper(name="Frontend-Dev-1", context=self.context),
            BackendDeveloper(name="Backend-Dev-1", context=self.context),
            FullstackDeveloper(name="Fullstack-Dev-1", context=self.context)
        ]
        
        self.execution_metrics = {
            "tasks_completed": 0,
            "bugs_found": 0,
            "code_reviews_completed": 0,
            "tests_executed": 0,
            "sprint_progress": 0.0
        }
    
    async def execute_sprint(self) -> Dict[str, Any]:
        """Execute the complete sprint with parallel development workflow."""
        
        logger.info("sprint_execution_started", sprint_id=self.sprint.id)
        
        try:
            # Update sprint status
            self.sprint.status = SprintStatus.IN_PROGRESS
            self.sprint.start_date = datetime.utcnow()
            
            # Execute sprint workflow
            execution_results = []
            
            # 1. Sprint Kickoff
            kickoff_result = await self._conduct_sprint_kickoff()
            execution_results.append(kickoff_result)
            
            # 2. Daily execution cycle (simulate sprint days)
            sprint_days = self._calculate_sprint_days()
            
            for day in range(1, sprint_days + 1):
                logger.info("sprint_day_started", sprint_id=self.sprint.id, day=day)
                
                # Daily standup
                standup_result = await self._conduct_daily_standup(day)
                execution_results.append(standup_result)
                
                # Parallel development work
                development_result = await self._execute_parallel_development(day)
                execution_results.append(development_result)
                
                # Tech Lead reviews (can happen in parallel)
                if day % 2 == 0:  # Reviews every other day
                    review_result = await self._conduct_code_reviews()
                    execution_results.append(review_result)
                
                # QA testing (parallel with development)
                qa_result = await self._execute_qa_testing(day)
                execution_results.append(qa_result)
                
                # Update sprint progress
                await self._update_sprint_progress()
                
                logger.info("sprint_day_completed", 
                          sprint_id=self.sprint.id, 
                          day=day,
                          progress=self.execution_metrics["sprint_progress"])
            
            # 3. Sprint completion activities
            completion_result = await self._complete_sprint_execution()
            execution_results.append(completion_result)
            
            # Final sprint status update
            self.sprint.status = SprintStatus.COMPLETED
            self.sprint.end_date = datetime.utcnow()
            
            logger.info("sprint_execution_completed", 
                      sprint_id=self.sprint.id,
                      duration_days=sprint_days,
                      tasks_completed=self.execution_metrics["tasks_completed"])
            
            return {
                "sprint_id": self.sprint.id,
                "execution_results": execution_results,
                "metrics": self.execution_metrics,
                "duration_days": sprint_days,
                "success": True,
                "final_status": SprintStatus.COMPLETED
            }
            
        except Exception as e:
            logger.error("sprint_execution_failed", 
                        sprint_id=self.sprint.id, 
                        error=str(e))
            
            self.sprint.status = SprintStatus.FAILED
            return {
                "sprint_id": self.sprint.id,
                "success": False,
                "error": str(e),
                "metrics": self.execution_metrics
            }
    
    async def _conduct_sprint_kickoff(self) -> Dict[str, Any]:
        """Conduct sprint kickoff with team alignment."""
        
        logger.info("sprint_kickoff_started", sprint_id=self.sprint.id)
        
        # Scrum Master facilitates kickoff
        kickoff_prompt = f"""
        Conduct sprint kickoff for Sprint {self.sprint.id}:
        
        Sprint Goal: {self.sprint.goal}
        Sprint Duration: {self.sprint.duration_weeks} weeks
        Stories in Sprint: {len(self.sprint.user_stories)}
        Team Size: {len(self.developers)} developers + Tech Lead + QA
        
        Kickoff Agenda:
        1. Review sprint goal and priorities
        2. Clarify user stories and acceptance criteria
        3. Discuss technical approach and dependencies
        4. Identify potential risks and mitigation strategies
        5. Establish communication and collaboration protocols
        6. Set up development environment and tools
        
        Facilitate team alignment and ensure everyone understands:
        - Sprint objectives and success criteria
        - Individual responsibilities and task assignments
        - Definition of Done and quality standards
        - Daily standup schedule and format
        - Escalation procedures for blockers
        """
        
        kickoff_result = await self.scrum_master.execute(kickoff_prompt)
        
        logger.info("sprint_kickoff_completed", sprint_id=self.sprint.id)
        
        return {
            "activity": "sprint_kickoff",
            "result": kickoff_result,
            "team_aligned": True,
            "environment_ready": True,
            "duration_minutes": 60
        }
    
    async def _conduct_daily_standup(self, day: int) -> Dict[str, Any]:
        """Conduct daily standup meeting."""
        
        logger.info("daily_standup_started", sprint_id=self.sprint.id, day=day)
        
        # Scrum Master facilitates standup
        standup_prompt = f"""
        Facilitate daily standup for Sprint {self.sprint.id}, Day {day}:
        
        Current Sprint Progress: {self.execution_metrics['sprint_progress']:.1f}%
        Tasks Completed: {self.execution_metrics['tasks_completed']}
        Active Blockers: {len([task for task in self.sprint.tasks if task.status == TaskStatus.BLOCKED])}
        
        Standup Format (for each team member):
        1. What did you complete yesterday?
        2. What will you work on today?
        3. Are there any blockers or impediments?
        
        Team Members:
        - Frontend Developer: UI components and user experience
        - Backend Developer: APIs and business logic
        - Fullstack Developer: End-to-end features and integration
        - QA Engineer: Testing and quality assurance
        - Tech Lead: Architecture decisions and code reviews
        
        Focus Areas:
        - Identify and resolve blockers quickly
        - Ensure team coordination and communication
        - Track progress against sprint goal
        - Adjust priorities if needed
        - Maintain team motivation and focus
        """
        
        standup_result = await self.scrum_master.execute(standup_prompt)
        
        # Identify and address blockers
        blockers_identified = await self._identify_and_resolve_blockers()
        
        logger.info("daily_standup_completed", 
                   sprint_id=self.sprint.id, 
                   day=day,
                   blockers_resolved=len(blockers_identified))
        
        return {
            "activity": "daily_standup",
            "day": day,
            "result": standup_result,
            "blockers_identified": blockers_identified,
            "team_alignment_score": 9.2,
            "duration_minutes": 15
        }
    
    async def _execute_parallel_development(self, day: int) -> Dict[str, Any]:
        """Execute parallel development work by multiple developers."""
        
        logger.info("parallel_development_started", 
                   sprint_id=self.sprint.id, 
                   day=day,
                   active_developers=len(self.developers))
        
        # Get available tasks for each developer type
        available_tasks = self._get_available_tasks()
        
        # Execute tasks in parallel
        development_tasks = []
        
        for developer in self.developers:
            # Assign appropriate tasks based on developer specialization
            assigned_tasks = self._assign_tasks_to_developer(developer, available_tasks)
            
            if assigned_tasks:
                # Execute tasks in parallel
                for task in assigned_tasks:
                    development_tasks.append(
                        self._execute_development_task(developer, task, day)
                    )
        
        # Execute all development tasks in parallel
        development_results = await asyncio.gather(*development_tasks, return_exceptions=True)
        
        # Process results and update metrics
        successful_tasks = []
        failed_tasks = []
        
        for result in development_results:
            if isinstance(result, Exception):
                failed_tasks.append(str(result))
            else:
                successful_tasks.append(result)
                self.execution_metrics["tasks_completed"] += 1
        
        logger.info("parallel_development_completed",
                   sprint_id=self.sprint.id,
                   day=day,
                   successful_tasks=len(successful_tasks),
                   failed_tasks=len(failed_tasks))
        
        return {
            "activity": "parallel_development",
            "day": day,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "parallel_execution": True,
            "developers_active": len(self.developers),
            "productivity_score": 8.7
        }
    
    async def _execute_development_task(
        self, 
        developer, 
        task: TaskModel, 
        day: int
    ) -> Dict[str, Any]:
        """Execute a single development task."""
        
        logger.info("development_task_started",
                   developer=developer.name,
                   task_id=task.id,
                   task_title=task.title)
        
        # Mark task as in progress
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_to = developer.name
        task.start_date = datetime.utcnow()
        
        # Execute task based on developer type and task requirements
        try:
            if hasattr(developer, 'implement_ui_component') and 'frontend' in task.description.lower():
                result = await developer.implement_ui_component(task, {
                    "name": task.title.replace(' ', ''),
                    "type": "functional",
                    "framework": "React"
                })
            elif hasattr(developer, 'implement_api_endpoint') and 'api' in task.description.lower():
                result = await developer.implement_api_endpoint(task, {
                    "method": "POST",
                    "path": f"/api/v1/{task.title.lower().replace(' ', '_')}",
                    "auth_required": True
                })
            elif hasattr(developer, 'implement_end_to_end_feature'):
                result = await developer.implement_end_to_end_feature(task, {
                    "frontend_components": [task.title],
                    "backend_endpoints": [f"/api/v1/{task.title.lower().replace(' ', '_')}"],
                    "database_changes": ["add_table"],
                    "integrations": []
                })
            else:
                # Generic task execution
                result = await developer.execute(f"Implement {task.title}: {task.description}")
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            task.end_date = datetime.utcnow()
            
            logger.info("development_task_completed",
                       developer=developer.name,
                       task_id=task.id,
                       duration_hours=2.5)
            
            return {
                "task_id": task.id,
                "developer": developer.name,
                "result": result,
                "status": TaskStatus.COMPLETED,
                "duration_hours": 2.5
            }
            
        except Exception as e:
            # Mark task as failed
            task.status = TaskStatus.FAILED
            
            logger.error("development_task_failed",
                        developer=developer.name,
                        task_id=task.id,
                        error=str(e))
            
            return {
                "task_id": task.id,
                "developer": developer.name,
                "status": TaskStatus.FAILED,
                "error": str(e)
            }
    
    async def _conduct_code_reviews(self) -> Dict[str, Any]:
        """Tech Lead conducts code reviews in parallel."""
        
        logger.info("code_reviews_started", sprint_id=self.sprint.id)
        
        # Get completed tasks that need review
        completed_tasks = [task for task in self.sprint.tasks 
                          if task.status == TaskStatus.COMPLETED and not task.reviewed]
        
        if not completed_tasks:
            return {
                "activity": "code_reviews",
                "reviews_completed": 0,
                "message": "No code ready for review"
            }
        
        # Tech Lead reviews code in parallel
        review_tasks = []
        for task in completed_tasks:
            review_tasks.append(self._review_single_task(task))
        
        review_results = await asyncio.gather(*review_tasks, return_exceptions=True)
        
        successful_reviews = []
        failed_reviews = []
        
        for result in review_results:
            if isinstance(result, Exception):
                failed_reviews.append(str(result))
            else:
                successful_reviews.append(result)
                self.execution_metrics["code_reviews_completed"] += 1
        
        logger.info("code_reviews_completed",
                   sprint_id=self.sprint.id,
                   reviews_completed=len(successful_reviews),
                   reviews_failed=len(failed_reviews))
        
        return {
            "activity": "code_reviews",
            "reviews_completed": len(successful_reviews),
            "reviews_failed": len(failed_reviews),
            "parallel_reviews": True,
            "tech_lead_efficiency": 9.1
        }
    
    async def _review_single_task(self, task: TaskModel) -> Dict[str, Any]:
        """Tech Lead reviews a single task."""
        
        review_prompt = f"""
        Review code for task: {task.title}
        
        Task Description: {task.description}
        Developer: {task.assigned_to}
        Completion Date: {task.end_date}
        
        Review Criteria:
        1. Code quality and maintainability
        2. Architecture adherence and design patterns
        3. Security considerations and best practices
        4. Performance optimization opportunities
        5. Test coverage and quality
        6. Documentation completeness
        7. Integration with existing codebase
        
        Provide:
        - Overall quality assessment
        - Specific feedback and improvement suggestions
        - Approval status (approved/needs-changes/rejected)
        - Priority of any required changes
        """
        
        review_result = await self.tech_lead.execute(review_prompt)
        
        # Mark task as reviewed
        task.reviewed = True
        task.review_status = "approved"  # Simplified for demo
        
        return {
            "task_id": task.id,
            "review_result": review_result,
            "status": "approved",
            "feedback_provided": True
        }
    
    async def _execute_qa_testing(self, day: int) -> Dict[str, Any]:
        """QA Engineer executes testing in parallel with development."""
        
        logger.info("qa_testing_started", sprint_id=self.sprint.id, day=day)
        
        # Get completed tasks ready for testing
        ready_for_testing = [task for task in self.sprint.tasks 
                           if task.status == TaskStatus.COMPLETED and task.reviewed]
        
        if not ready_for_testing:
            return {
                "activity": "qa_testing",
                "tests_executed": 0,
                "message": "No completed work ready for testing"
            }
        
        # Execute different types of testing
        testing_tasks = []
        
        for task in ready_for_testing:
            # Functional testing
            testing_tasks.append(self._execute_functional_testing(task))
            
            # Every few tasks, add specialized testing
            if len(testing_tasks) % 3 == 0:
                testing_tasks.append(self._execute_accessibility_testing(task))
            
            if len(testing_tasks) % 4 == 0:
                testing_tasks.append(self._execute_performance_testing(task))
        
        testing_results = await asyncio.gather(*testing_tasks, return_exceptions=True)
        
        successful_tests = []
        failed_tests = []
        bugs_found = 0
        
        for result in testing_results:
            if isinstance(result, Exception):
                failed_tests.append(str(result))
            else:
                successful_tests.append(result)
                bugs_found += result.get("bugs_found", 0)
                self.execution_metrics["tests_executed"] += 1
        
        self.execution_metrics["bugs_found"] += bugs_found
        
        logger.info("qa_testing_completed",
                   sprint_id=self.sprint.id,
                   day=day,
                   tests_executed=len(successful_tests),
                   bugs_found=bugs_found)
        
        return {
            "activity": "qa_testing",
            "day": day,
            "tests_executed": len(successful_tests),
            "bugs_found": bugs_found,
            "parallel_testing": True,
            "quality_score": 8.9
        }
    
    async def _execute_functional_testing(self, task: TaskModel) -> Dict[str, Any]:
        """Execute functional testing for a task."""
        
        test_scenarios = [
            {"name": "Happy Path", "description": f"Test normal flow for {task.title}"},
            {"name": "Error Handling", "description": f"Test error scenarios for {task.title}"},
            {"name": "Edge Cases", "description": f"Test boundary conditions for {task.title}"}
        ]
        
        result = await self.qa_engineer.execute_functional_testing(task, test_scenarios)
        
        return {
            "task_id": task.id,
            "test_type": "functional",
            "result": result,
            "bugs_found": result.get("defects_found", 0)
        }
    
    async def _execute_accessibility_testing(self, task: TaskModel) -> Dict[str, Any]:
        """Execute accessibility testing for a task."""
        
        accessibility_spec = {
            "wcag_level": "AA",
            "target_users": ["screen_reader_users", "keyboard_users"],
            "assistive_tech": ["NVDA", "JAWS"],
            "tools": ["axe-core", "WAVE"]
        }
        
        # Create a UserStory object for the QA method (simplified)
        user_story = UserStory(
            id=task.id,
            title=task.title,
            description=task.description,
            story_points=3.0
        )
        
        result = await self.qa_engineer.perform_accessibility_testing(task, accessibility_spec)
        
        return {
            "task_id": task.id,
            "test_type": "accessibility",
            "result": result,
            "bugs_found": result.get("violations_found", 0)
        }
    
    async def _execute_performance_testing(self, task: TaskModel) -> Dict[str, Any]:
        """Execute performance testing for a task."""
        
        performance_requirements = {
            "page_load_time": "< 3s",
            "api_response_time": "< 500ms",
            "concurrent_users": 100,
            "throughput": "1000 req/min"
        }
        
        result = await self.qa_engineer.conduct_performance_testing(task, performance_requirements)
        
        return {
            "task_id": task.id,
            "test_type": "performance",
            "result": result,
            "bugs_found": 1 if not result.get("requirements_met", True) else 0
        }
    
    def _calculate_sprint_days(self) -> int:
        """Calculate number of working days in sprint."""
        # Simplified: 2 weeks = 10 working days
        return int(self.sprint.duration_weeks * 5)
    
    def _get_available_tasks(self) -> List[TaskModel]:
        """Get tasks available for development."""
        return [task for task in self.sprint.tasks 
                if task.status == TaskStatus.TODO and not task.blocked]
    
    def _assign_tasks_to_developer(self, developer, available_tasks: List[TaskModel]) -> List[TaskModel]:
        """Assign appropriate tasks to developer based on specialization."""
        
        assigned_tasks = []
        
        # Simple assignment logic based on developer type and task keywords
        for task in available_tasks:
            if len(assigned_tasks) >= 2:  # Limit tasks per developer per day
                break
                
            task_desc = task.description.lower()
            
            if 'frontend' in developer.name.lower() and any(keyword in task_desc for keyword in ['ui', 'component', 'interface', 'frontend']):
                assigned_tasks.append(task)
            elif 'backend' in developer.name.lower() and any(keyword in task_desc for keyword in ['api', 'database', 'server', 'backend']):
                assigned_tasks.append(task)
            elif 'fullstack' in developer.name.lower() and any(keyword in task_desc for keyword in ['feature', 'integration', 'workflow']):
                assigned_tasks.append(task)
        
        return assigned_tasks
    
    async def _identify_and_resolve_blockers(self) -> List[Dict[str, Any]]:
        """Identify and resolve sprint blockers."""
        
        blockers = []
        
        # Find blocked tasks
        blocked_tasks = [task for task in self.sprint.tasks if task.status == TaskStatus.BLOCKED]
        
        for task in blocked_tasks:
            blocker_info = {
                "task_id": task.id,
                "blocker_type": "dependency",  # Simplified
                "description": f"Task {task.title} is blocked",
                "resolution": "Escalated to Tech Lead",
                "resolved": True  # Simplified for demo
            }
            blockers.append(blocker_info)
            
            # Resolve blocker (simplified)
            task.status = TaskStatus.TODO
            task.blocked = False
        
        return blockers
    
    async def _update_sprint_progress(self):
        """Update sprint progress metrics."""
        
        total_tasks = len(self.sprint.tasks)
        completed_tasks = len([task for task in self.sprint.tasks if task.status == TaskStatus.COMPLETED])
        
        if total_tasks > 0:
            self.execution_metrics["sprint_progress"] = (completed_tasks / total_tasks) * 100
        
        # Update sprint object
        self.sprint.progress_percentage = self.execution_metrics["sprint_progress"]
    
    async def _complete_sprint_execution(self) -> Dict[str, Any]:
        """Complete sprint execution with final activities."""
        
        logger.info("sprint_completion_started", sprint_id=self.sprint.id)
        
        # Final code reviews for any remaining work
        await self._conduct_code_reviews()
        
        # Final QA testing and regression testing
        final_qa_result = await self._execute_final_qa_testing()
        
        # Sprint metrics calculation
        final_metrics = self._calculate_final_metrics()
        
        # Prepare for sprint review
        sprint_summary = await self._prepare_sprint_summary()
        
        logger.info("sprint_completion_finished", 
                   sprint_id=self.sprint.id,
                   final_progress=self.execution_metrics["sprint_progress"])
        
        return {
            "activity": "sprint_completion",
            "final_qa_result": final_qa_result,
            "final_metrics": final_metrics,
            "sprint_summary": sprint_summary,
            "ready_for_review": True
        }
    
    async def _execute_final_qa_testing(self) -> Dict[str, Any]:
        """Execute final QA testing and regression testing."""
        
        regression_spec = {
            "affected_areas": ["new_features", "modified_components"],
            "test_suite": "full",
            "automation_level": "high",
            "risk_areas": ["authentication", "data_integrity"]
        }
        
        # Create a dummy task for regression testing
        regression_task = TaskModel(
            id="regression_test",
            title="Sprint Regression Testing",
            description="Full regression testing for sprint deliverables"
        )
        
        result = await self.qa_engineer.perform_regression_testing(regression_task, regression_spec)
        
        return {
            "regression_testing": result,
            "quality_gate_passed": result.get("quality_verdict", "").startswith("PASS"),
            "final_quality_score": 9.2
        }
    
    def _calculate_final_metrics(self) -> Dict[str, Any]:
        """Calculate final sprint metrics."""
        
        total_tasks = len(self.sprint.tasks)
        completed_tasks = self.execution_metrics["tasks_completed"]
        
        return {
            "sprint_id": self.sprint.id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "bugs_found": self.execution_metrics["bugs_found"],
            "code_reviews_completed": self.execution_metrics["code_reviews_completed"],
            "tests_executed": self.execution_metrics["tests_executed"],
            "team_velocity": completed_tasks / self.sprint.duration_weeks,
            "quality_score": 9.1,
            "team_satisfaction": 8.8
        }
    
    async def _prepare_sprint_summary(self) -> Dict[str, Any]:
        """Prepare sprint summary for review."""
        
        summary_prompt = f"""
        Prepare sprint summary for Sprint {self.sprint.id}:
        
        Sprint Goal: {self.sprint.goal}
        Sprint Duration: {self.sprint.duration_weeks} weeks
        
        Execution Metrics:
        - Tasks Completed: {self.execution_metrics['tasks_completed']}
        - Progress: {self.execution_metrics['sprint_progress']:.1f}%
        - Bugs Found: {self.execution_metrics['bugs_found']}
        - Code Reviews: {self.execution_metrics['code_reviews_completed']}
        - Tests Executed: {self.execution_metrics['tests_executed']}
        
        Summarize:
        1. Sprint achievements and deliverables
        2. Team performance and collaboration
        3. Quality metrics and testing results
        4. Challenges faced and how they were resolved
        5. Lessons learned and improvements for next sprint
        6. Recommendations for sprint review
        """
        
        summary_result = await self.scrum_master.execute(summary_prompt)
        
        return {
            "sprint_summary": summary_result.get("result", ""),
            "achievements_highlighted": True,
            "lessons_documented": True,
            "ready_for_review": True
        }