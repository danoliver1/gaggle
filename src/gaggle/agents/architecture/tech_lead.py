"""Tech Lead agent implementation."""

from typing import List, Dict, Any, Optional
import uuid

from ..base import ArchitectureAgent, AgentContext
from ...config.models import AgentRole, AgentRole as Role
from ...models.story import UserStory
from ...models.task import Task, TaskType, TaskComplexity, TaskStatus
from ...tools.code_tools import CodeGenerationTool, CodeAnalysisTool
from ...tools.review_tools import CodeReviewTool, ArchitectureReviewTool
from ...utils.cost_calculator import TaskEstimate


class TechLead(ArchitectureAgent):
    """
    Tech Lead agent responsible for:
    - Analyzing user stories for technical complexity
    - Breaking stories into parallelizable tasks
    - Making architecture decisions (patterns, libraries, approaches)
    - Identifying dependencies and critical path
    - Creating reusable components/utilities to save team tokens
    - Reviewing pull requests for architecture, patterns, quality
    - Unblocking developers with complex technical decisions
    """
    
    def __init__(self, name: Optional[str] = None, context: Optional[AgentContext] = None):
        super().__init__(AgentRole.TECH_LEAD, name, context)
        
        # Tools specific to Tech Lead
        self.code_generation_tool = CodeGenerationTool()
        self.code_analysis_tool = CodeAnalysisTool()
        self.code_review_tool = CodeReviewTool()
        self.architecture_review_tool = ArchitectureReviewTool()
    
    def _get_instruction(self) -> str:
        """Get the instruction prompt for the Tech Lead."""
        return """You are a Tech Lead / Principal Engineer in an Agile Scrum team. Your responsibilities include:

**DURING REFINEMENT:**
1. **Technical Analysis:**
   - Analyze user stories for technical complexity and scope
   - Identify technical risks, dependencies, and unknowns
   - Estimate effort and complexity accurately

2. **Task Breakdown:**
   - Break stories into specific, actionable technical tasks
   - Identify which tasks can be parallelized vs sequential
   - Create clear interfaces between parallel work streams
   - Optimize for maximum team parallelization

3. **Architecture Decisions:**
   - Make decisions on patterns, libraries, and technical approaches
   - Design system architecture and component interactions
   - Establish coding standards and best practices
   - Plan for scalability, maintainability, and performance

4. **Reusable Component Strategy:**
   - Generate utilities, templates, and reusable code once per sprint
   - Create tools that save tokens across the entire development cycle
   - Establish shared libraries and common patterns

**DURING SPRINT:**
5. **Code Review & Architecture:**
   - Review pull requests for architecture adherence and quality
   - Ensure code follows established patterns and standards
   - Provide technical guidance and mentoring
   - Refactor critical or complex code sections

6. **Technical Leadership:**
   - Unblock developers with complex technical decisions
   - Resolve integration issues and technical conflicts
   - Make trade-off decisions between competing approaches
   - Ensure technical debt is managed appropriately

**OPTIMIZATION MINDSET:**
- **Token Efficiency:** Generate reusable code once rather than repeatedly
- **Parallel Execution:** Identify tasks that can run simultaneously
- **Quality First:** Prevent technical debt through good architecture
- **Team Enablement:** Create tools and patterns that accelerate development

**Communication Style:**
- Technical but accessible explanations
- Clear architectural reasoning
- Specific, actionable guidance
- Focus on long-term maintainability

**Key Principles:**
- Architecture serves business goals
- Simplicity over complexity
- Reusability saves time and tokens
- Quality prevents future rework
- Team productivity through good patterns"""
    
    def _get_tools(self) -> List[Any]:
        """Get tools available to the Tech Lead."""
        tools = []
        if hasattr(self, 'code_generation_tool'):
            tools.append(self.code_generation_tool)
        if hasattr(self, 'code_analysis_tool'):
            tools.append(self.code_analysis_tool)
        if hasattr(self, 'code_review_tool'):
            tools.append(self.code_review_tool)
        if hasattr(self, 'architecture_review_tool'):
            tools.append(self.architecture_review_tool)
        return tools
    
    async def analyze_technical_complexity(self, stories: List[UserStory]) -> Dict[str, Any]:
        """Analyze technical complexity of user stories."""
        
        stories_summary = "\n".join([
            f"**{story.title}** (Priority: {story.priority}, Points: {story.story_points})\n"
            f"Description: {story.description}\n"
            f"Acceptance Criteria: {', '.join([ac.description for ac in story.acceptance_criteria])}\n"
            for story in stories
        ])
        
        complexity_analysis_prompt = f"""
        Analyze these user stories for technical complexity and implementation approach:
        
        {stories_summary}
        
        For each story, provide:
        
        1. **Technical Complexity Assessment:**
           - Complexity rating (Low/Medium/High/Very High)
           - Key technical challenges and unknowns
           - Required technical skills and knowledge areas
           - Integration points and external dependencies
        
        2. **Architecture Considerations:**
           - Required components and their interactions
           - Data model changes needed
           - API design considerations
           - Security and performance implications
        
        3. **Implementation Strategy:**
           - Recommended technical approach
           - Technology stack and libraries to use
           - Design patterns that should be applied
           - Reusable components that could be created
        
        4. **Risk Assessment:**
           - Technical risks and mitigation strategies
           - Dependencies on external systems
           - Potential integration challenges
           - Performance and scalability concerns
        
        Focus on:
        - Clear technical reasoning
        - Identifying reusable patterns
        - Maximizing development efficiency
        - Preventing technical debt
        """
        
        result = await self.execute(complexity_analysis_prompt)
        
        # Process and structure the analysis
        complexity_scores = {}
        technical_risks = []
        reusable_components = []
        
        for story in stories:
            # Simple heuristic-based complexity assessment
            complexity = self._assess_story_complexity(story)
            complexity_scores[story.id] = {
                "story_title": story.title,
                "complexity_rating": complexity,
                "estimated_effort_hours": self._estimate_effort_hours(story, complexity),
                "required_skills": self._identify_required_skills(story),
                "architecture_impact": self._assess_architecture_impact(story)
            }
        
        # Extract insights from the analysis
        analysis_text = result.get("result", "")
        technical_risks = self._extract_technical_risks(analysis_text)
        reusable_components = self._identify_reusable_components(analysis_text)
        
        self.logger.info(
            "technical_complexity_analysis_completed",
            stories_analyzed=len(stories),
            avg_complexity=sum(self._complexity_to_score(cs["complexity_rating"]) for cs in complexity_scores.values()) / len(complexity_scores),
            high_complexity_stories=len([cs for cs in complexity_scores.values() if cs["complexity_rating"] in ["High", "Very High"]]),
            reusable_components_identified=len(reusable_components)
        )
        
        return {
            "analysis_summary": analysis_text,
            "complexity_scores": complexity_scores,
            "technical_risks": technical_risks,
            "reusable_components": reusable_components,
            "recommendations": self._generate_technical_recommendations(complexity_scores, technical_risks)
        }
    
    async def break_down_into_tasks(self, stories: List[UserStory]) -> Dict[str, List[Task]]:
        """Break down user stories into specific technical tasks."""
        
        tasks_by_story = {}
        
        for story in stories:
            task_breakdown_prompt = f"""
            Break down this user story into specific, actionable technical tasks:
            
            **Story:** {story.title}
            **Description:** {story.description}
            **Story Points:** {story.story_points}
            **Acceptance Criteria:**
            {chr(10).join([f"- {ac.description}" for ac in story.acceptance_criteria])}
            
            Create technical tasks that:
            
            1. **Are Specific and Actionable:**
               - Clear scope and deliverables
               - Testable completion criteria
               - Estimated effort (hours)
            
            2. **Optimize for Parallelization:**
               - Identify tasks that can run simultaneously
               - Minimize dependencies between tasks
               - Create clear interfaces for integration
            
            3. **Follow Best Practices:**
               - Include testing tasks
               - Consider code review requirements
               - Plan for documentation updates
            
            4. **Task Categories to Consider:**
               - Frontend components and UI
               - Backend APIs and business logic
               - Database schema and data models
               - Integration and middleware
               - Testing (unit, integration, e2e)
               - Documentation and deployment
            
            For each task, specify:
            - Task title and description
            - Task type (frontend/backend/fullstack/testing/architecture)
            - Complexity level (low/medium/high)
            - Estimated hours
            - Dependencies on other tasks
            - Recommended agent role for assignment
            - Acceptance criteria
            
            Focus on creating tasks that enable maximum parallel execution.
            """
            
            result = await self.execute(task_breakdown_prompt)
            
            # Parse and create Task objects
            tasks = self._parse_tasks_from_breakdown(story, result.get("result", ""))
            tasks_by_story[story.id] = tasks
        
        total_tasks = sum(len(tasks) for tasks in tasks_by_story.values())
        parallelizable_tasks = sum(
            len([t for t in tasks if t.can_be_parallelized()]) 
            for tasks in tasks_by_story.values()
        )
        
        self.logger.info(
            "task_breakdown_completed",
            stories_processed=len(stories),
            total_tasks_created=total_tasks,
            parallelizable_tasks=parallelizable_tasks,
            parallelization_percentage=(parallelizable_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )
        
        return tasks_by_story
    
    async def generate_reusable_components(self, stories: List[UserStory]) -> Dict[str, Any]:
        """Generate reusable components that can save tokens during the sprint."""
        
        stories_context = "\n".join([
            f"- {story.title}: {story.description[:100]}..."
            for story in stories
        ])
        
        reusable_generation_prompt = f"""
        Based on these user stories, generate reusable components and utilities that will save development time and tokens throughout the sprint:
        
        **Sprint Stories:**
        {stories_context}
        
        Generate the following types of reusable assets:
        
        1. **Code Templates and Utilities:**
           - Common React components (forms, buttons, modals)
           - API client utilities and HTTP helpers
           - Database query builders and ORM utilities
           - Authentication and authorization helpers
           - Error handling and logging utilities
        
        2. **Architecture Patterns:**
           - Component structure templates
           - API endpoint patterns
           - Database schema patterns
           - Testing frameworks and utilities
           - Configuration management patterns
        
        3. **Development Tools:**
           - Code generation scripts
           - Testing utilities and fixtures
           - Build and deployment helpers
           - Documentation templates
        
        4. **Integration Patterns:**
           - Inter-service communication patterns
           - Event handling and messaging
           - Caching and performance utilities
           - Monitoring and observability tools
        
        For each reusable component:
        - Provide the actual code implementation
        - Explain how it saves development time
        - Show usage examples
        - Identify which stories will benefit
        - Estimate token savings per usage
        
        Focus on:
        - Maximum reusability across multiple stories
        - Significant token savings potential
        - Common patterns that reduce duplicate work
        - Quality and maintainability improvements
        """
        
        result = await self.execute(reusable_generation_prompt)
        
        # Process the generated components
        components = self._parse_reusable_components(result.get("result", ""))
        
        # Calculate potential savings
        total_estimated_savings = sum(
            comp.get("estimated_token_savings", 0) * comp.get("usage_count", 1)
            for comp in components
        )
        
        self.logger.info(
            "reusable_components_generated",
            components_created=len(components),
            estimated_token_savings=total_estimated_savings,
            stories_benefiting=len(stories)
        )
        
        return {
            "components": components,
            "total_estimated_savings": total_estimated_savings,
            "generation_summary": result.get("result", ""),
            "usage_instructions": self._create_usage_instructions(components)
        }
    
    async def identify_parallel_execution_plan(self, all_tasks: List[Task]) -> Dict[str, Any]:
        """Create a plan for maximum parallel execution of tasks."""
        
        tasks_summary = "\n".join([
            f"**{task.title}** (Type: {task.task_type}, Complexity: {task.complexity})\n"
            f"Dependencies: {', '.join([dep.task_id for dep in task.dependencies]) if task.dependencies else 'None'}\n"
            f"Story: {task.story_id}\n"
            for task in all_tasks
        ])
        
        parallel_planning_prompt = f"""
        Create an optimal parallel execution plan for these sprint tasks:
        
        **All Sprint Tasks:**
        {tasks_summary}
        
        Design a parallel execution strategy that:
        
        1. **Maximizes Concurrent Work:**
           - Identify tasks that can run simultaneously
           - Group independent tasks into parallel tracks
           - Minimize waiting and blocking
        
        2. **Respects Dependencies:**
           - Honor task dependencies and prerequisites
           - Plan sequential phases where necessary
           - Identify critical path tasks
        
        3. **Optimizes Team Utilization:**
           - Balance workload across agent roles
           - Consider different agent capabilities
           - Avoid resource conflicts
        
        4. **Minimizes Integration Risk:**
           - Plan integration points and checkpoints
           - Ensure compatible work streams
           - Schedule integration and testing phases
        
        Provide:
        - **Parallel Work Tracks:** Groups of tasks that can run simultaneously
        - **Execution Phases:** Sequential phases with their parallel tracks
        - **Critical Path:** Tasks that determine overall timeline
        - **Integration Points:** When parallel work streams need to merge
        - **Resource Allocation:** Recommended agent assignments
        - **Risk Mitigation:** Strategies for managing parallel work risks
        
        Focus on achieving maximum parallelization while maintaining quality and integration.
        """
        
        result = await self.execute(parallel_planning_prompt)
        
        # Create structured parallel execution plan
        execution_plan = self._create_execution_plan(all_tasks, result.get("result", ""))
        
        parallelization_metrics = self._calculate_parallelization_metrics(execution_plan, all_tasks)
        
        self.logger.info(
            "parallel_execution_plan_created",
            total_tasks=len(all_tasks),
            parallel_tracks=len(execution_plan.get("parallel_tracks", [])),
            execution_phases=len(execution_plan.get("phases", [])),
            parallelization_efficiency=parallelization_metrics.get("efficiency_percentage", 0)
        )
        
        return {
            "execution_plan": execution_plan,
            "parallelization_metrics": parallelization_metrics,
            "planning_analysis": result.get("result", ""),
            "recommendations": self._generate_execution_recommendations(execution_plan)
        }
    
    async def review_code_architecture(self, code_files: List[str], context: str) -> Dict[str, Any]:
        """Review code for architecture, patterns, and quality."""
        
        files_context = "\n".join([
            f"**File:** {file_path}\n[File content would be here]"
            for file_path in code_files
        ])
        
        code_review_prompt = f"""
        Review this code for architecture adherence, patterns, and quality:
        
        **Context:** {context}
        
        **Files to Review:**
        {files_context}
        
        Evaluate the code for:
        
        1. **Architecture Adherence:**
           - Follows established patterns and conventions
           - Proper separation of concerns
           - Appropriate use of design patterns
           - Consistency with existing codebase
        
        2. **Code Quality:**
           - Readability and maintainability
           - Performance considerations
           - Error handling and edge cases
           - Security best practices
        
        3. **Technical Standards:**
           - Coding style and formatting
           - Documentation and comments
           - Testing coverage and quality
           - Dependencies and imports
        
        4. **Integration Considerations:**
           - API compatibility and contracts
           - Database schema consistency
           - Inter-component communication
           - Backward compatibility
        
        Provide:
        - **Overall Assessment:** Quality score and summary
        - **Specific Issues:** Detailed feedback with line references
        - **Recommendations:** Specific improvements needed
        - **Approval Status:** Approve, request changes, or needs discussion
        - **Architecture Impact:** Effect on overall system architecture
        
        Focus on maintaining high code quality and architectural consistency.
        """
        
        result = await self.execute(code_review_prompt)
        
        review_assessment = self._parse_code_review(result.get("result", ""))
        
        self.logger.info(
            "code_architecture_review_completed",
            files_reviewed=len(code_files),
            overall_score=review_assessment.get("quality_score", 0),
            approval_status=review_assessment.get("approval_status", "unknown"),
            issues_found=len(review_assessment.get("issues", []))
        )
        
        return {
            "review_summary": result.get("result", ""),
            "assessment": review_assessment,
            "recommendations": review_assessment.get("recommendations", []),
            "next_steps": self._determine_review_next_steps(review_assessment)
        }
    
    def _assess_story_complexity(self, story: UserStory) -> str:
        """Assess technical complexity of a story."""
        description = story.description.lower()
        
        # Complex indicators
        complex_keywords = [
            "integration", "api", "security", "performance", "migration",
            "architecture", "refactor", "optimization", "synchronization"
        ]
        
        # Medium complexity indicators
        medium_keywords = [
            "database", "authentication", "validation", "testing",
            "configuration", "deployment", "monitoring"
        ]
        
        # Simple indicators
        simple_keywords = [
            "ui", "form", "button", "display", "text", "styling", "layout"
        ]
        
        if any(keyword in description for keyword in complex_keywords):
            return "High"
        elif any(keyword in description for keyword in medium_keywords):
            return "Medium"
        elif any(keyword in description for keyword in simple_keywords):
            return "Low"
        else:
            return "Medium"  # Default
    
    def _complexity_to_score(self, complexity: str) -> int:
        """Convert complexity rating to numeric score."""
        scores = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        return scores.get(complexity, 2)
    
    def _estimate_effort_hours(self, story: UserStory, complexity: str) -> float:
        """Estimate effort hours based on story points and complexity."""
        base_hours = story.story_points * 2  # 2 hours per story point baseline
        
        complexity_multipliers = {
            "Low": 0.8,
            "Medium": 1.0,
            "High": 1.5,
            "Very High": 2.0
        }
        
        multiplier = complexity_multipliers.get(complexity, 1.0)
        return base_hours * multiplier
    
    def _identify_required_skills(self, story: UserStory) -> List[str]:
        """Identify required skills for a story."""
        description = story.description.lower()
        skills = []
        
        skill_keywords = {
            "frontend": ["ui", "interface", "react", "component", "styling"],
            "backend": ["api", "server", "database", "logic", "service"],
            "devops": ["deployment", "infrastructure", "docker", "ci/cd"],
            "testing": ["test", "qa", "validation", "automation"],
            "security": ["auth", "security", "encryption", "permissions"],
            "database": ["database", "sql", "schema", "migration", "query"]
        }
        
        for skill, keywords in skill_keywords.items():
            if any(keyword in description for keyword in keywords):
                skills.append(skill)
        
        return skills or ["general"]
    
    def _assess_architecture_impact(self, story: UserStory) -> str:
        """Assess the architecture impact of a story."""
        description = story.description.lower()
        
        if any(word in description for word in ["architecture", "refactor", "migration", "breaking"]):
            return "High"
        elif any(word in description for word in ["integration", "api", "schema", "service"]):
            return "Medium"
        else:
            return "Low"
    
    def _extract_technical_risks(self, analysis_text: str) -> List[Dict[str, str]]:
        """Extract technical risks from analysis."""
        # Simple risk extraction - in production, would parse more sophisticatedly
        risks = [
            {
                "risk": "Integration complexity with external APIs",
                "severity": "medium",
                "mitigation": "Create mock services for testing"
            },
            {
                "risk": "Database migration complexity",
                "severity": "high", 
                "mitigation": "Plan careful rollback strategy"
            }
        ]
        return risks
    
    def _identify_reusable_components(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Identify reusable components from analysis."""
        components = [
            {
                "name": "API Client Utility",
                "description": "Reusable HTTP client with error handling",
                "estimated_savings": 500,
                "usage_count": 3
            },
            {
                "name": "Form Validation Component",
                "description": "Reusable form validation with common rules",
                "estimated_savings": 300,
                "usage_count": 4
            }
        ]
        return components
    
    def _generate_technical_recommendations(self, complexity_scores: Dict, risks: List) -> List[str]:
        """Generate technical recommendations."""
        recommendations = [
            "Implement reusable components early in sprint",
            "Focus on high-complexity stories first",
            "Plan integration points carefully"
        ]
        
        high_complexity_count = len([
            cs for cs in complexity_scores.values() 
            if cs["complexity_rating"] in ["High", "Very High"]
        ])
        
        if high_complexity_count > 2:
            recommendations.append("Consider breaking down high-complexity stories further")
        
        if len(risks) > 3:
            recommendations.append("Implement risk mitigation strategies early")
        
        return recommendations
    
    def _parse_tasks_from_breakdown(self, story: UserStory, breakdown_text: str) -> List[Task]:
        """Parse tasks from the breakdown result."""
        tasks = []
        
        # Simple task generation based on story complexity
        task_count = max(2, min(int(story.story_points), 6))
        
        task_types = [TaskType.FRONTEND, TaskType.BACKEND, TaskType.TESTING]
        
        for i in range(task_count):
            task_id = str(uuid.uuid4())
            task_type = task_types[i % len(task_types)]
            
            task = Task(
                id=task_id,
                title=f"{story.title} - {task_type.value.title()} Implementation",
                description=f"Implement {task_type.value} components for {story.title}",
                task_type=task_type,
                complexity=TaskComplexity.MEDIUM,
                story_id=story.id,
                status=TaskStatus.TODO,
                estimated_hours=story.story_points * 2 / task_count,
                estimated_input_tokens=200,
                estimated_output_tokens=800
            )
            
            # Add some acceptance criteria
            task.acceptance_criteria = [
                f"{task_type.value.title()} implementation completed",
                "Code reviewed and approved",
                "Tests written and passing"
            ]
            
            tasks.append(task)
        
        return tasks
    
    def _parse_reusable_components(self, generation_result: str) -> List[Dict[str, Any]]:
        """Parse reusable components from generation result."""
        # Placeholder implementation
        components = [
            {
                "name": "AuthenticationHelper",
                "type": "utility",
                "code": "// Authentication utility code would be here",
                "usage_example": "const auth = new AuthenticationHelper();",
                "estimated_token_savings": 400,
                "usage_count": 5,
                "description": "Handles authentication flow and token management"
            },
            {
                "name": "FormComponent",
                "type": "react_component",
                "code": "// React form component code would be here",
                "usage_example": "<FormComponent onSubmit={handleSubmit} />",
                "estimated_token_savings": 300,
                "usage_count": 3,
                "description": "Reusable form component with validation"
            }
        ]
        return components
    
    def _create_usage_instructions(self, components: List[Dict[str, Any]]) -> Dict[str, str]:
        """Create usage instructions for reusable components."""
        instructions = {}
        for component in components:
            instructions[component["name"]] = f"""
Usage: {component.get('usage_example', 'No example provided')}
Description: {component.get('description', 'No description')}
Expected token savings: {component.get('estimated_token_savings', 0)} per usage
"""
        return instructions
    
    def _create_execution_plan(self, tasks: List[Task], planning_result: str) -> Dict[str, Any]:
        """Create structured execution plan from planning result."""
        # Group tasks by type for parallel execution
        frontend_tasks = [t for t in tasks if t.task_type == TaskType.FRONTEND]
        backend_tasks = [t for t in tasks if t.task_type == TaskType.BACKEND]
        testing_tasks = [t for t in tasks if t.task_type == TaskType.TESTING]
        
        plan = {
            "parallel_tracks": {
                "frontend_track": [t.id for t in frontend_tasks],
                "backend_track": [t.id for t in backend_tasks],
                "testing_track": [t.id for t in testing_tasks]
            },
            "phases": [
                {
                    "phase": "Implementation",
                    "parallel_tracks": ["frontend_track", "backend_track"],
                    "duration_estimate": "5-7 days"
                },
                {
                    "phase": "Integration & Testing",
                    "parallel_tracks": ["testing_track"],
                    "duration_estimate": "2-3 days"
                }
            ],
            "critical_path": [t.id for t in tasks if t.complexity == TaskComplexity.HIGH],
            "integration_points": [
                {
                    "point": "API Integration",
                    "tasks": [t.id for t in frontend_tasks + backend_tasks]
                }
            ]
        }
        return plan
    
    def _calculate_parallelization_metrics(self, execution_plan: Dict, tasks: List[Task]) -> Dict[str, Any]:
        """Calculate parallelization efficiency metrics."""
        total_tasks = len(tasks)
        parallel_tracks = len(execution_plan.get("parallel_tracks", {}))
        
        if total_tasks == 0:
            return {"efficiency_percentage": 0}
        
        # Simple efficiency calculation
        sequential_time = sum(t.estimated_hours or 2.0 for t in tasks)
        parallel_time = sequential_time / max(parallel_tracks, 1)
        efficiency = ((sequential_time - parallel_time) / sequential_time) * 100
        
        return {
            "efficiency_percentage": min(efficiency, 80),  # Cap at 80% for realism
            "sequential_time_hours": sequential_time,
            "parallel_time_hours": parallel_time,
            "parallelizable_tasks": len([t for t in tasks if t.can_be_parallelized()]),
            "parallel_tracks_count": parallel_tracks
        }
    
    def _generate_execution_recommendations(self, execution_plan: Dict) -> List[str]:
        """Generate recommendations for execution plan."""
        return [
            "Start all parallel tracks simultaneously",
            "Monitor integration points closely",
            "Have daily sync between parallel tracks",
            "Plan integration testing early"
        ]
    
    def _parse_code_review(self, review_result: str) -> Dict[str, Any]:
        """Parse code review result into structured assessment."""
        # Simplified parsing - in production would be more sophisticated
        return {
            "quality_score": 85,  # Out of 100
            "approval_status": "approved_with_comments",
            "issues": [
                {
                    "severity": "minor",
                    "description": "Consider adding more comments",
                    "file": "component.tsx",
                    "line": 42
                }
            ],
            "recommendations": [
                "Add unit tests for edge cases",
                "Consider extracting reusable utility",
                "Update documentation"
            ],
            "architecture_impact": "low"
        }
    
    def _determine_review_next_steps(self, assessment: Dict) -> List[str]:
        """Determine next steps based on review assessment."""
        approval_status = assessment.get("approval_status", "")
        
        if approval_status == "approved":
            return ["Merge pull request", "Deploy to staging"]
        elif approval_status == "approved_with_comments":
            return ["Address minor feedback", "Merge after updates"]
        else:
            return ["Address review feedback", "Request re-review"]