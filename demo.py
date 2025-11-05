#!/usr/bin/env python3
"""
Gaggle Demo Script

Demonstrates the core Gaggle workflow:
1. Product Owner analyzes requirements and creates user stories
2. Tech Lead performs technical analysis and task breakdown
3. Scrum Master facilitates sprint planning
4. Show sprint metrics and parallel execution plan

This demo runs without external APIs to show the architecture.
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import Gaggle components
from src.gaggle.agents.base import AgentContext
from src.gaggle.agents.coordination.product_owner import ProductOwner
from src.gaggle.agents.coordination.scrum_master import ScrumMaster
from src.gaggle.agents.architecture.tech_lead import TechLead
from src.gaggle.models.team import TeamConfiguration
from src.gaggle.models.sprint import SprintModel, SprintStatus
from src.gaggle.utils.logging import setup_logging

console = Console()

async def demo_sprint_planning():
    """Demonstrate complete sprint planning workflow."""
    
    console.print(Panel.fit(
        "🦆 [bold blue]Gaggle Demo[/bold blue] - AI-Powered Agile Development Team\n"
        "Simulating complete Scrum sprint planning workflow",
        border_style="blue"
    ))
    
    # Product idea for the demo
    product_idea = """
    Build a modern task management application that helps remote teams collaborate effectively.
    The app should include user authentication, project creation, task assignment, 
    real-time notifications, and progress tracking with analytics dashboard.
    """
    
    console.print(f"\n📋 [bold]Product Idea:[/bold]\n{product_idea.strip()}")
    
    # Initialize shared context and team
    context = AgentContext("demo_sprint_001")
    team_config = TeamConfiguration.create_default_team()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Phase 1: Product Owner Analysis
        task1 = progress.add_task("🎯 Product Owner analyzing requirements...", total=None)
        
        po = ProductOwner(context=context)
        
        # Mock the agent execution for demo purposes
        class MockResult:
            def get(self, key, default=None):
                if key == "result":
                    return """
                    **Product Analysis Complete**
                    
                    Key user personas identified:
                    - Remote team members needing task coordination
                    - Project managers requiring oversight capabilities
                    - Team leads needing progress visibility
                    
                    Core value propositions:
                    - Improved remote team collaboration
                    - Real-time project visibility
                    - Streamlined task management
                    
                    Priority features for MVP:
                    1. User authentication and team setup
                    2. Project and task management
                    3. Real-time notifications
                    4. Basic analytics dashboard
                    """
                return default
        
        # Simulate analysis (in real deployment, this would call LLM APIs)
        po.execute = lambda _prompt, **_kwargs: MockResult()
        
        await po.analyze_requirements(product_idea)
        progress.update(task1, description="✅ Requirements analyzed")
        
        # Create user stories
        task2 = progress.add_task("📝 Creating user stories...", total=None)
        stories = await po.create_user_stories(product_idea)
        progress.update(task2, description=f"✅ Created {len(stories)} user stories")
        
        # Prioritize backlog
        task3 = progress.add_task("🎯 Prioritizing backlog...", total=None)
        prioritized_stories = await po.prioritize_backlog(stories)
        progress.update(task3, description="✅ Backlog prioritized")
        
        # Phase 2: Tech Lead Technical Analysis
        task4 = progress.add_task("🏗️  Tech Lead analyzing complexity...", total=None)
        
        tech_lead = TechLead(context=context)
        tech_lead.execute = lambda _prompt, **_kwargs: MockResult()
        
        complexity_analysis = await tech_lead.analyze_technical_complexity(prioritized_stories)
        progress.update(task4, description="✅ Technical complexity analyzed")
        
        # Break down into tasks
        task5 = progress.add_task("🔧 Breaking down into tasks...", total=None)
        tasks_by_story = await tech_lead.break_down_into_tasks(prioritized_stories)
        progress.update(task5, description="✅ Tasks created")
        
        # Generate reusable components
        task6 = progress.add_task("🧩 Generating reusable components...", total=None)
        reusable_components = await tech_lead.generate_reusable_components(prioritized_stories)
        progress.update(task6, description="✅ Reusable components generated")
        
        # Create parallel execution plan
        all_tasks = []
        for tasks in tasks_by_story.values():
            all_tasks.extend(tasks)
        
        task7 = progress.add_task("⚡ Creating parallel execution plan...", total=None)
        parallel_plan = await tech_lead.identify_parallel_execution_plan(all_tasks)
        progress.update(task7, description="✅ Parallel execution plan created")
        
        # Phase 3: Scrum Master Sprint Planning
        task8 = progress.add_task("📅 Scrum Master creating sprint plan...", total=None)
        
        scrum_master = ScrumMaster(context=context)
        scrum_master.execute = lambda _prompt, **_kwargs: MockResult()
        
        sprint_plan = await scrum_master.facilitate_sprint_planning(
            prioritized_stories, team_config, 10
        )
        progress.update(task8, description="✅ Sprint plan created")
    
    # Create sprint model
    sprint = SprintModel(
        id="SPRINT-001",
        goal=sprint_plan['sprint_goal'],
        status=SprintStatus.PLANNING
    )
    
    for story in prioritized_stories:
        sprint.add_story(story)
    
    for tasks in tasks_by_story.values():
        for task in tasks:
            sprint.add_task(task)
    
    # Display Results
    console.print("\n🎉 [bold green]Sprint Planning Complete![/bold green]")
    
    # Sprint Goal
    console.print(Panel(
        f"[bold blue]{sprint.goal}[/bold blue]",
        title="🎯 Sprint Goal",
        border_style="blue"
    ))
    
    # User Stories
    stories_table = Table(title="📚 Sprint Backlog - User Stories")
    stories_table.add_column("Story", style="cyan", width=30)
    stories_table.add_column("Priority", style="magenta")
    stories_table.add_column("Points", style="green")
    stories_table.add_column("Complexity", style="yellow")
    stories_table.add_column("Tasks", style="blue")
    
    for story in prioritized_stories:
        complexity = complexity_analysis['complexity_scores'].get(story.id, {}).get('complexity_rating', 'Medium')
        task_count = len(tasks_by_story.get(story.id, []))
        
        stories_table.add_row(
            story.title,
            story.priority.value,
            str(story.story_points),
            complexity,
            str(task_count)
        )
    
    console.print(stories_table)
    
    # Technical Tasks Breakdown
    tasks_table = Table(title="🔧 Technical Tasks")
    tasks_table.add_column("Task", style="cyan", width=35)
    tasks_table.add_column("Type", style="magenta")
    tasks_table.add_column("Complexity", style="yellow")
    tasks_table.add_column("Story", style="blue", width=20)
    tasks_table.add_column("Parallelizable", style="green")
    
    for story_id, tasks in tasks_by_story.items():
        story_title = next((s.title for s in prioritized_stories if s.id == story_id), "Unknown")
        for task in tasks:
            tasks_table.add_row(
                task.title,
                task.task_type.value,
                task.complexity.value,
                story_title[:20] + "..." if len(story_title) > 20 else story_title,
                "✅" if task.can_be_parallelized() else "❌"
            )
    
    console.print(tasks_table)
    
    # Reusable Components
    components_table = Table(title="🧩 Reusable Components Generated")
    components_table.add_column("Component", style="cyan")
    components_table.add_column("Type", style="magenta")
    components_table.add_column("Token Savings", style="green")
    components_table.add_column("Usage Count", style="blue")
    
    for component in reusable_components['components']:
        components_table.add_row(
            component['name'],
            component['type'],
            f"{component['estimated_token_savings']:,}",
            str(component['usage_count'])
        )
    
    console.print(components_table)
    
    # Sprint Metrics
    metrics_table = Table(title="📊 Sprint Metrics & Efficiency")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="green")
    
    total_tasks = len(all_tasks)
    parallelizable_tasks = len([t for t in all_tasks if t.can_be_parallelized()])
    total_story_points = sum(story.story_points for story in prioritized_stories)
    total_estimated_savings = reusable_components['total_estimated_savings']
    
    metrics_table.add_row("Sprint Duration", "10 days")
    metrics_table.add_row("Total User Stories", str(len(prioritized_stories)))
    metrics_table.add_row("Total Story Points", str(total_story_points))
    metrics_table.add_row("Total Tasks Created", str(total_tasks))
    metrics_table.add_row("Parallelizable Tasks", f"{parallelizable_tasks} ({parallelizable_tasks/total_tasks*100:.1f}%)")
    metrics_table.add_row("Reusable Components", str(len(reusable_components['components'])))
    metrics_table.add_row("Estimated Token Savings", f"{total_estimated_savings:,}")
    metrics_table.add_row("Team Size", str(len(team_config.members)))
    
    console.print(metrics_table)
    
    # Parallel Execution Plan
    parallel_metrics = parallel_plan['parallelization_metrics']
    
    efficiency_table = Table(title="⚡ Parallel Execution Efficiency")
    efficiency_table.add_column("Aspect", style="cyan")
    efficiency_table.add_column("Sequential", style="red")
    efficiency_table.add_column("Parallel", style="green")
    efficiency_table.add_column("Improvement", style="blue")
    
    sequential_time = parallel_metrics['sequential_time_hours']
    parallel_time = parallel_metrics['parallel_time_hours']
    efficiency_gain = parallel_metrics['efficiency_percentage']
    
    efficiency_table.add_row(
        "Estimated Time",
        f"{sequential_time:.1f} hours",
        f"{parallel_time:.1f} hours",
        f"{efficiency_gain:.1f}% faster"
    )
    efficiency_table.add_row(
        "Parallel Tracks",
        "1 track",
        f"{parallel_metrics['parallel_tracks_count']} tracks",
        f"{parallel_metrics['parallel_tracks_count']}x parallelism"
    )
    
    console.print(efficiency_table)
    
    # Team Allocation
    team_table = Table(title="👥 Team Allocation")
    team_table.add_column("Agent", style="cyan")
    team_table.add_column("Role", style="magenta")
    team_table.add_column("Model Tier", style="yellow")
    team_table.add_column("Status", style="green")
    team_table.add_column("Specializations", style="blue")
    
    for member in team_config.members:
        specializations = ", ".join(member.specializations[:2]) + ("..." if len(member.specializations) > 2 else "")
        team_table.add_row(
            member.name,
            member.role.value,
            member.model_tier.value,
            member.status.value,
            specializations
        )
    
    console.print(team_table)
    
    # Architecture Insights
    console.print(Panel(
        """[bold]🏗️  Architecture Highlights:[/bold]

• [green]Token Efficiency:[/green] Reusable components save ~{:,} tokens across sprint
• [blue]Parallelization:[/blue] {:d}% of tasks can run simultaneously
• [yellow]Cost Optimization:[/yellow] Strategic model tier assignments by agent role
• [magenta]Quality Focus:[/magenta] Tech Lead review pattern ensures architecture consistency

[bold]🚀 Next Steps:[/bold]
1. Begin sprint execution with parallel task assignment
2. Conduct daily standups for coordination
3. Monitor progress through sprint board
4. Perform code reviews and integration testing""".format(
            total_estimated_savings,
            int(parallelizable_tasks/total_tasks*100)
        ),
        title="Sprint Planning Summary",
        border_style="green"
    ))
    
    # Context usage summary
    console.print(f"\n💰 [bold]Token Usage Summary:[/bold]")
    console.print(f"   Total Tokens: {context.token_counter.get_total_tokens():,}")
    console.print(f"   Estimated Cost: ${context.token_counter.get_total_cost():.2f}")
    
    cost_breakdown = context.token_counter.get_cost_breakdown()
    if cost_breakdown:
        console.print("   Cost by Role:")
        for role, data in cost_breakdown.items():
            console.print(f"     {role}: ${data['cost']:.2f} ({data['model_tier']})")


async def main():
    """Main demo function."""
    try:
        # Setup logging
        setup_logging()
        
        # Run the demo
        await demo_sprint_planning()
        
        console.print("\n✨ [bold green]Demo completed successfully![/bold green]")
        console.print("🔗 Explore the codebase at: https://github.com/danoliver1/gaggle")
        
    except Exception as e:
        console.print(f"\n❌ [bold red]Demo failed:[/bold red] {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())