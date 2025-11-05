#!/usr/bin/env python3
"""
Gaggle CLI Demo

Demonstrates the CLI interface without requiring external dependencies.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize CLI app
app = typer.Typer(
    name="gaggle",
    help="🦆 Gaggle: AI-Powered Agile Development Team",
    add_completion=False,
)

console = Console()

@app.callback()
def main():
    """Gaggle: AI-Powered Agile Development Team that simulates complete Scrum workflows."""
    console.print(Panel.fit(
        "🦆 [bold blue]Gaggle[/bold blue] - AI-Powered Agile Development Team\n"
        "Simulates complete Scrum workflows with multi-agent collaboration",
        border_style="blue"
    ))

@app.command()
def init(
    repo_url: str = typer.Argument(..., help="GitHub repository URL"),
    github_token: str = typer.Option("demo-token", "--token", help="GitHub personal access token"),
):
    """Initialize Gaggle for a repository."""
    console.print("🚀 Initializing Gaggle...")
    console.print(f"📁 Repository: {repo_url}")
    console.print("✅ Gaggle initialized successfully!")
    
    # Display team summary
    team_table = Table(title="Team Configuration")
    team_table.add_column("Agent", style="cyan")
    team_table.add_column("Role", style="magenta")
    team_table.add_column("Model Tier", style="green")
    
    team_members = [
        ("ProductOwner", "coordination", "haiku"),
        ("ScrumMaster", "coordination", "haiku"),
        ("TechLead", "architecture", "opus"),
        ("FrontendDev", "implementation", "sonnet"),
        ("BackendDev", "implementation", "sonnet"),
        ("QAEngineer", "quality_assurance", "sonnet"),
    ]
    
    for name, role, tier in team_members:
        team_table.add_row(name, role, tier)
    
    console.print(team_table)

@app.command() 
def sprint(
    action: str = typer.Argument(..., help="Sprint action: plan, execute, review, or status"),
    goal: str = typer.Option("Build a demo application", "--goal", help="Sprint goal"),
):
    """Manage sprint lifecycle."""
    console.print(f"📋 Sprint Action: {action}")
    console.print(f"🎯 Goal: {goal}")
    
    if action == "plan":
        console.print("✅ Sprint planning completed!")
        
        # Mock sprint plan results
        results_table = Table(title="Sprint Planning Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")
        
        results_table.add_row("User Stories Created", "6")
        results_table.add_row("Total Story Points", "32")
        results_table.add_row("Tasks Created", "18")
        results_table.add_row("Estimated Duration", "10 days")
        results_table.add_row("Parallelizable Tasks", "12 (67%)")
        results_table.add_row("Estimated Token Savings", "2,500+")
        
        console.print(results_table)
        
    else:
        console.print(f"⚠️ Action '{action}' would execute the full workflow")
        console.print("💡 Try: uv run python simple_demo.py for a full demonstration")

@app.command()
def team():
    """Show team status."""
    console.print("👥 Team Status")
    
    status_table = Table()
    status_table.add_column("Agent", style="cyan")
    status_table.add_column("Role", style="magenta")
    status_table.add_column("Status", style="green")
    status_table.add_column("Model Tier", style="yellow")
    
    team_status = [
        ("ProductOwner", "coordination", "available", "haiku"),
        ("ScrumMaster", "coordination", "available", "haiku"),
        ("TechLead", "architecture", "available", "opus"),
        ("FrontendDev", "implementation", "available", "sonnet"),
        ("BackendDev", "implementation", "available", "sonnet"),
        ("QAEngineer", "quality_assurance", "available", "sonnet"),
    ]
    
    for name, role, status, tier in team_status:
        status_table.add_row(name, role, status, tier)
    
    console.print(status_table)

@app.command()
def demo():
    """Run the interactive demo."""
    console.print("🚀 Running Gaggle Demo...")
    console.print("💡 Execute: [bold]uv run python simple_demo.py[/bold]")

if __name__ == "__main__":
    app()