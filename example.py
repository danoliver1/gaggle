from strands import Agent
from strands.models import BedrockModel

# Model tiers matched to roles
haiku = BedrockModel(model_id="claude-haiku")  # Coordination/facilitation
sonnet = BedrockModel(model_id="claude-sonnet")  # Implementation work
opus = BedrockModel(model_id="claude-opus")  # Architecture & review

# ============================================
# COORDINATION LAYER (Cheap - Haiku)
# ============================================

product_owner = Agent(
    name="ProductOwner",
    model=haiku,
    instruction="""You are a Product Owner. Your responsibilities:
    1. Ask clarifying questions about business value
    2. Write user stories with clear acceptance criteria
    3. Prioritize backlog based on business value
    4. Accept/reject work during sprint review""",
    tools=[backlog_tool, story_template_tool],
)

scrum_master = Agent(
    name="ScrumMaster",
    model=haiku,
    instruction="""You are the Scrum Master. You facilitate:
    1. Sprint planning, standups, retros
    2. Remove impediments
    3. Track sprint metrics (velocity, burndown)
    4. Ensure scrum ceremonies run smoothly
    5. Protect the team from distractions""",
    tools=[sprint_board_tool, metrics_tool, blocker_tracker],
)

# ============================================
# ARCHITECTURE & REVIEW LAYER (Expensive - Opus)
# ============================================

tech_lead = Agent(
    name="TechLead",
    model=opus,  # 🎯 Most powerful model
    instruction="""You are the Tech Lead / Principal Engineer. You:
    
    DURING REFINEMENT:
    1. Analyze user stories for technical complexity
    2. Break stories into parallelizable tasks
    3. Make architecture decisions (patterns, libraries, approaches)
    4. Identify dependencies and critical path
    5. Create reusable components/utilities to save team tokens
    6. Estimate complexity and assign to appropriate developers
    
    DURING SPRINT:
    7. Review pull requests for architecture, patterns, quality
    8. Unblock developers with complex technical decisions
    9. Refactor critical/complex code sections
    10. Ensure code follows established patterns
    
    OPTIMIZATION MINDSET:
    - Generate reusable code once (saves tokens across sprint)
    - Identify which tasks can run in parallel
    - Determine if simple code generation would be more efficient than LLM calls""",
    tools=[
        architecture_tool,
        task_breakdown_tool,
        code_review_tool,
        reusable_component_generator,  # Creates Python tools
        dependency_analyzer,
    ],
)

# ============================================
# IMPLEMENTATION LAYER (Mid-tier - Sonnet)
# Multiple developers doing bulk of work
# ============================================

developer_frontend = Agent(
    name="FrontendDev",
    model=sonnet,  # 🎯 Good for implementation
    instruction="""You are a mid-level frontend developer. You:
    1. Implement features from technical tasks
    2. Write unit tests
    3. Follow patterns established by Tech Lead
    4. Ask Tech Lead for architectural guidance when stuck
    5. Submit code for Tech Lead review
    6. Fix issues found in code review""",
    tools=[
        code_implementation_tool,
        component_tool,
        styling_tool,
        unit_test_tool,
        git_tool,
    ],
)

developer_backend = Agent(
    name="BackendDev",
    model=sonnet,  # 🎯 Good for implementation
    instruction="""You are a mid-level backend developer. You:
    1. Implement APIs and business logic from tasks
    2. Write unit and integration tests
    3. Use reusable utilities created by Tech Lead
    4. Follow established patterns and conventions
    5. Ask Tech Lead for guidance on complex logic
    6. Submit code for review""",
    tools=[
        api_implementation_tool,
        database_tool,
        auth_tool,
        integration_test_tool,
        git_tool,
    ],
)

developer_fullstack = Agent(
    name="FullstackDev",
    model=sonnet,  # 🎯 Good for implementation
    instruction="""You are a mid-level fullstack developer...""",
    tools=[],  # TODO: add appropriate tools
)

# ============================================
# QUALITY ASSURANCE LAYER (Mid-tier - Sonnet)
# ============================================

qa_engineer = Agent(
    name="QAEngineer",
    model=sonnet,  # Needs good analytical skills
    instruction="""You are the QA Engineer. You:
    1. Review acceptance criteria during refinement
    2. Create test plans for stories
    3. Execute manual and automated tests (in parallel)
    4. Report bugs with clear reproduction steps
    5. Verify bug fixes
    6. Perform regression testing""",
    tools=[test_plan_tool, automated_test_tool, manual_test_tool, bug_reporting_tool],
)

# ============================================
# SPRINT WORKFLOW
# ============================================


class AgileSprint:

    def sprint_planning(self, product_idea):
        """Sprint Planning - Refinement & Task Breakdown"""

        # 1. PO creates and clarifies stories (cheap)
        user_stories = product_owner.create_stories(product_idea)

        # 2. Tech Lead does deep analysis (expensive but once per story)
        refined_stories = []
        for story in user_stories:
            # Tech Lead analyzes and breaks down
            analysis = tech_lead(
                f"""
                Analyze this story and:
                1. Identify technical complexity
                2. Break into parallelizable tasks
                3. Create any reusable utilities needed
                4. Determine dependencies
                
                Story: {story}
            """
            )

            refined_stories.append(analysis)

        # 3. Tech Lead generates reusable components ONCE
        # (Expensive now, but saves tokens during sprint)
        reusable_code = tech_lead.generate_reusable_components(refined_stories)

        # 4. Scrum Master creates sprint plan
        sprint_plan = scrum_master.create_sprint_plan(
            stories=refined_stories,
            reusable_code=reusable_code,
            capacity={"frontend": 2, "backend": 2, "fullstack": 1, "qa": 1},
        )

        return sprint_plan

    async def run_sprint(self, sprint_plan):
        """Execute sprint with maximum parallelism"""

        # Get parallel task groups from Tech Lead's analysis
        parallel_groups = sprint_plan.parallel_task_groups

        for day in range(1, 11):  # 2-week sprint
            # Daily standup (cheap)
            scrum_master.daily_standup()

            # Execute current day's parallel tasks
            current_tasks = self.get_tasks_for_day(parallel_groups, day)

            # ALL DEVELOPERS WORK IN PARALLEL
            dev_results = await asyncio.gather(
                *[self.assign_to_developer(task) for task in current_tasks]
            )

            # TECH LEAD REVIEWS CODE (expensive but essential)
            review_results = await asyncio.gather(
                *[tech_lead.review_code(result) for result in dev_results]
            )

            # Developers fix issues (parallel)
            fixes = await asyncio.gather(
                *[
                    self.assign_to_developer(review.fix_task)
                    for review in review_results
                    if review.needs_changes
                ]
            )

            # QA TESTS IN PARALLEL
            test_results = await asyncio.gather(
                *[
                    qa_engineer.test_feature(result)
                    for result in dev_results
                    if result.ready_for_test
                ]
            )

    def assign_to_developer(self, task):
        """Route task to appropriate developer"""
        if task.type == "frontend":
            return developer_frontend(task)
        elif task.type == "backend":
            return developer_backend(task)
        elif task.type == "fullstack":
            return developer_fullstack(task)

    def sprint_review_and_retro(self):
        """End of sprint ceremonies"""
        # PO reviews completed work (cheap)
        demo_results = product_owner.review_sprint()

        # Scrum Master facilitates retro (cheap)
        improvements = scrum_master.retrospective(
            [
                tech_lead,
                developer_frontend,
                developer_backend,
                developer_fullstack,
                qa_engineer,
            ]
        )

        return demo_results, improvements
