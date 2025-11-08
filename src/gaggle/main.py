"""Gaggle CLI application entry point."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .agents.architecture.tech_lead import TechLead
from .agents.coordination.product_owner import ProductOwner
from .agents.coordination.scrum_master import ScrumMaster
from .config.settings import settings
from .models.team import TeamConfiguration
from .utils.logging import get_logger, setup_logging

# Initialize CLI app
app = typer.Typer(
    name="gaggle",
    help="🦆 Gaggle: AI-Powered Agile Development Team",
    add_completion=False,
)

console = Console()
logger = get_logger("gaggle_cli")


@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
    log_level: str = typer.Option("INFO", "--log-level", help="Set log level"),
):
    """Gaggle: AI-Powered Agile Development Team that simulates complete Scrum workflows."""

    # Setup logging
    if debug:
        settings.debug_mode = True
        settings.log_level = "DEBUG"
    else:
        settings.log_level = log_level.upper()

    setup_logging()

    # Display banner
    console.print(
        Panel.fit(
            "🦆 [bold blue]Gaggle[/bold blue] - AI-Powered Agile Development Team\n"
            "Simulates complete Scrum workflows with multi-agent collaboration",
            border_style="blue",
        )
    )


@app.command()
def init(
    repo_url: str = typer.Argument(..., help="GitHub repository URL"),
    github_token: str = typer.Option(
        ..., "--token", envvar="GITHUB_TOKEN", help="GitHub personal access token"
    ),
    anthropic_key: str | None = typer.Option(
        None, "--anthropic-key", envvar="ANTHROPIC_API_KEY", help="Anthropic API key"
    ),
    aws_profile: str | None = typer.Option(
        None, "--aws-profile", envvar="AWS_PROFILE", help="AWS profile for Bedrock"
    ),
):
    """Initialize Gaggle for a repository."""

    console.print("🚀 Initializing Gaggle...")

    # Parse repository info
    try:
        from .models.github import GitHubRepository

        repo = GitHubRepository.from_url(repo_url)
        console.print(f"📁 Repository: {repo.full_name}")
    except ValueError as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)

    # Validate API credentials
    if not anthropic_key and not aws_profile:
        console.print(
            "❌ Error: Either --anthropic-key or --aws-profile must be provided",
            style="red",
        )
        raise typer.Exit(1)

    # Update settings
    settings.github_token = github_token
    settings.github_repo = repo.name
    settings.github_org = repo.owner

    if anthropic_key:
        settings.anthropic_api_key = anthropic_key
    if aws_profile:
        settings.aws_profile = aws_profile

    # Create default team configuration
    team_config = TeamConfiguration.create_default_team()

    console.print("✅ Gaggle initialized successfully!")
    console.print(f"📊 Team configured with {len(team_config.members)} agents")

    # Display team summary
    team_table = Table(title="Team Configuration")
    team_table.add_column("Agent", style="cyan")
    team_table.add_column("Role", style="magenta")
    team_table.add_column("Model Tier", style="green")

    for member in team_config.members:
        team_table.add_row(member.name, member.role.value, member.model_tier.value)

    console.print(team_table)


@app.command()
def sprint(
    action: str = typer.Argument(
        ..., help="Sprint action: plan, execute, review, or status"
    ),
    goal: str | None = typer.Option(None, "--goal", help="Sprint goal or product idea"),
    duration: int = typer.Option(10, "--duration", help="Sprint duration in days"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
):
    """Manage sprint lifecycle (plan, execute, review, status)."""

    if dry_run:
        settings.dry_run = True
        console.print("🔍 Running in dry-run mode (no changes will be made)")

    if action == "plan":
        if not goal:
            console.print(
                "❌ Error: --goal is required for sprint planning", style="red"
            )
            raise typer.Exit(1)

        asyncio.run(plan_sprint(goal, duration))

    elif action == "execute":
        console.print("🏃 Executing sprint...")
        console.print("⚠️  Sprint execution not yet implemented", style="yellow")

    elif action == "review":
        console.print("📋 Reviewing sprint...")
        console.print("⚠️  Sprint review not yet implemented", style="yellow")

    elif action == "status":
        console.print("📊 Sprint status...")
        console.print("⚠️  Sprint status not yet implemented", style="yellow")

    else:
        console.print(f"❌ Error: Unknown action '{action}'", style="red")
        console.print("Valid actions: plan, execute, review, status")
        raise typer.Exit(1)


async def plan_sprint(goal: str, duration: int):
    """Execute sprint planning workflow."""

    console.print(f"📋 Planning sprint with goal: [bold]{goal}[/bold]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Step 1: Product Owner analyzes requirements
        task1 = progress.add_task(
            "🎯 Product Owner analyzing requirements...", total=None
        )

        try:
            from .agents.base import AgentContext

            # Create shared context for the sprint
            context = AgentContext("sprint_planning_demo")

            # Initialize Product Owner
            po = ProductOwner(context=context)

            # Analyze requirements
            await po.analyze_requirements(goal)
            progress.update(task1, description="✅ Requirements analyzed")

            # Create user stories
            task2 = progress.add_task("📝 Creating user stories...", total=None)
            stories = await po.create_user_stories(goal)
            progress.update(
                task2, description=f"✅ Created {len(stories)} user stories"
            )

            # Prioritize backlog
            task3 = progress.add_task("🎯 Prioritizing backlog...", total=None)
            prioritized_stories = await po.prioritize_backlog(stories)
            progress.update(task3, description="✅ Backlog prioritized")

            # Step 2: Tech Lead technical analysis
            task4 = progress.add_task(
                "🏗️  Tech Lead analyzing complexity...", total=None
            )

            tech_lead = TechLead(context=context)
            complexity_analysis = await tech_lead.analyze_technical_complexity(
                prioritized_stories
            )
            progress.update(task4, description="✅ Technical complexity analyzed")

            # Break down into tasks
            task5 = progress.add_task("🔧 Breaking down into tasks...", total=None)
            tasks_by_story = await tech_lead.break_down_into_tasks(prioritized_stories)
            progress.update(task5, description="✅ Tasks created")

            # Generate reusable components
            task6 = progress.add_task(
                "🧩 Generating reusable components...", total=None
            )
            reusable_components = await tech_lead.generate_reusable_components(
                prioritized_stories
            )
            progress.update(task6, description="✅ Reusable components generated")

            # Step 3: Scrum Master creates sprint plan
            task7 = progress.add_task(
                "📅 Scrum Master creating sprint plan...", total=None
            )

            scrum_master = ScrumMaster(context=context)
            team_config = TeamConfiguration.create_default_team()

            sprint_plan = await scrum_master.facilitate_sprint_planning(
                prioritized_stories, team_config, duration
            )
            progress.update(task7, description="✅ Sprint plan created")

        except Exception as e:
            console.print(f"❌ Error during sprint planning: {e}", style="red")
            raise typer.Exit(1)

    # Display results
    console.print("\n🎉 Sprint Planning Complete!")

    # Sprint Goal
    console.print(
        Panel(
            f"[bold blue]{sprint_plan['sprint_goal']}[/bold blue]",
            title="Sprint Goal",
            border_style="blue",
        )
    )

    # User Stories Summary
    stories_table = Table(title="Sprint Backlog")
    stories_table.add_column("Story", style="cyan")
    stories_table.add_column("Priority", style="magenta")
    stories_table.add_column("Points", style="green")
    stories_table.add_column("Complexity", style="yellow")

    for story in prioritized_stories[:5]:  # Show first 5 stories
        complexity = (
            complexity_analysis["complexity_scores"]
            .get(story.id, {})
            .get("complexity_rating", "Unknown")
        )
        stories_table.add_row(
            story.title, story.priority.value, str(story.story_points), complexity
        )

    console.print(stories_table)

    # Sprint Metrics
    metrics_table = Table(title="Sprint Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="green")

    total_tasks = sum(len(tasks) for tasks in tasks_by_story.values())
    sum(story.story_points for story in prioritized_stories[:5])

    metrics_table.add_row(
        "Estimated Velocity", f"{sprint_plan['estimated_velocity']} points"
    )
    metrics_table.add_row("Total Tasks", str(total_tasks))
    metrics_table.add_row("Sprint Duration", f"{duration} days")
    metrics_table.add_row(
        "Reusable Components", str(len(reusable_components["components"]))
    )
    metrics_table.add_row(
        "Estimated Token Savings", f"{reusable_components['total_estimated_savings']:,}"
    )

    console.print(metrics_table)

    # Next Steps
    console.print(
        Panel(
            "1. Review and approve sprint plan\n"
            "2. Set up GitHub project board\n"
            "3. Begin sprint execution\n"
            "4. Conduct daily standups",
            title="Next Steps",
            border_style="green",
        )
    )


@app.command()
def team(
    action: str = typer.Argument(
        ..., help="Team action: status, add, remove, or configure"
    ),
    member_name: str | None = typer.Option(None, "--name", help="Team member name"),
    role: str | None = typer.Option(None, "--role", help="Agent role"),
):
    """Manage team configuration."""

    if action == "status":
        # Display team status
        team_config = TeamConfiguration.create_default_team()

        console.print("👥 Team Status")

        status_table = Table()
        status_table.add_column("Agent", style="cyan")
        status_table.add_column("Role", style="magenta")
        status_table.add_column("Status", style="green")
        status_table.add_column("Tasks Completed", style="blue")
        status_table.add_column("Total Cost", style="yellow")

        for member in team_config.members:
            status_table.add_row(
                member.name,
                member.role.value,
                member.status.value,
                str(member.tasks_completed),
                f"${member.total_cost:.2f}",
            )

        console.print(status_table)

        # Team workload summary
        workload = team_config.get_team_workload()
        console.print(f"\n📊 Team Utilization: {workload['utilization_rate']:.1f}%")
        console.print(f"🔄 Available: {workload['available_members']}")
        console.print(f"⚙️  Busy: {workload['busy_members']}")
        console.print(f"🚫 Blocked: {workload['blocked_members']}")

    else:
        console.print(f"⚠️  Team action '{action}' not yet implemented", style="yellow")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    set_key: str | None = typer.Option(None, "--set", help="Set configuration key"),
    value: str | None = typer.Option(None, "--value", help="Configuration value"),
):
    """Manage Gaggle configuration."""

    if show:
        console.print("⚙️  Current Configuration")

        config_table = Table()
        config_table.add_column("Setting", style="cyan")
        config_table.add_column("Value", style="green")

        # Show safe configuration values (no secrets)
        config_table.add_row("GitHub Repo", settings.github_repo or "Not set")
        config_table.add_row("GitHub Org", settings.github_org or "Not set")
        config_table.add_row(
            "Default Sprint Duration", f"{settings.default_sprint_duration} days"
        )
        config_table.add_row("Max Parallel Tasks", str(settings.max_parallel_tasks))
        config_table.add_row("Default Team Size", str(settings.default_team_size))
        config_table.add_row("Log Level", settings.log_level)
        config_table.add_row("Debug Mode", str(settings.debug_mode))
        config_table.add_row("Dry Run", str(settings.dry_run))

        console.print(config_table)

    elif set_key and value:
        console.print("⚠️  Configuration updates not yet implemented", style="yellow")

    else:
        console.print(
            "❌ Use --show to view config or --set with --value to update", style="red"
        )


if __name__ == "__main__":
    app()
