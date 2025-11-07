"""CI/CD pipeline integration for Gaggle sprint workflows."""

import asyncio
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime, timedelta
import structlog
import json

from ..models.sprint import Sprint, Task, UserStory
from ..config.settings import settings
from ..utils.logging import get_logger


class PipelineProvider(str, Enum):
    """Supported CI/CD pipeline providers."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"
    AZURE_DEVOPS = "azure_devops"
    CIRCLECI = "circleci"


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


class DeploymentEnvironment(str, Enum):
    """Deployment environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    FEATURE_BRANCH = "feature_branch"


logger = structlog.get_logger(__name__)


class PipelineConfiguration:
    """Configuration for CI/CD pipeline setup."""
    
    def __init__(
        self,
        provider: PipelineProvider,
        environments: List[DeploymentEnvironment],
        auto_deploy_on_sprint_completion: bool = True,
        run_tests_on_pr: bool = True,
        quality_gates: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.environments = environments
        self.auto_deploy_on_sprint_completion = auto_deploy_on_sprint_completion
        self.run_tests_on_pr = run_tests_on_pr
        self.quality_gates = quality_gates or {
            "test_coverage_threshold": 80,
            "code_quality_score": 7.5,
            "security_scan_required": True,
            "performance_regression_check": True
        }


class PipelineExecution:
    """Represents a pipeline execution instance."""
    
    def __init__(
        self,
        pipeline_id: str,
        provider: PipelineProvider,
        environment: DeploymentEnvironment,
        sprint_id: Optional[str] = None,
        user_story_id: Optional[str] = None,
        task_id: Optional[str] = None
    ):
        self.pipeline_id = pipeline_id
        self.provider = provider
        self.environment = environment
        self.sprint_id = sprint_id
        self.user_story_id = user_story_id
        self.task_id = task_id
        self.status = PipelineStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.logs: List[str] = []
        self.artifacts: Dict[str, str] = {}
        self.metrics: Dict[str, Any] = {}


class GitHubActionsPipeline:
    """GitHub Actions pipeline integration."""
    
    def __init__(self):
        self.logger = get_logger("github_actions")
    
    async def create_sprint_workflow(self, sprint: Sprint) -> str:
        """Create GitHub Actions workflow for sprint."""
        
        workflow_content = self._generate_sprint_workflow_yaml(sprint)
        
        # In production, this would use GitHub API to create the workflow file
        workflow_path = f".github/workflows/sprint-{sprint.id}.yml"
        
        self.logger.info(
            "sprint_workflow_created",
            sprint_id=sprint.id,
            workflow_path=workflow_path,
            story_count=len(sprint.user_stories)
        )
        
        return workflow_path
    
    def _generate_sprint_workflow_yaml(self, sprint: Sprint) -> str:
        """Generate GitHub Actions workflow YAML for sprint."""
        
        workflow = {
            "name": f"Sprint {sprint.id} CI/CD",
            "on": {
                "push": {
                    "branches": [f"sprint/{sprint.id}", "main"]
                },
                "pull_request": {
                    "branches": ["main"]
                }
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Set up Python", "uses": "actions/setup-python@v4", "with": {"python-version": "3.11"}},
                        {"name": "Install dependencies", "run": "pip install -r requirements.txt"},
                        {"name": "Run tests", "run": "pytest --cov=src --cov-report=xml"},
                        {"name": "Upload coverage", "uses": "codecov/codecov-action@v3"}
                    ]
                },
                "security-scan": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Run security scan", "run": "bandit -r src/"}
                    ]
                },
                "deploy-staging": {
                    "needs": ["test", "security-scan"],
                    "runs-on": "ubuntu-latest",
                    "if": "github.ref == 'refs/heads/main'",
                    "environment": "staging",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {"name": "Deploy to staging", "run": "echo 'Deploying to staging...'"}
                    ]
                }
            }
        }
        
        return json.dumps(workflow, indent=2)
    
    async def trigger_deployment(
        self, 
        environment: DeploymentEnvironment,
        sprint_id: str,
        artifacts: Dict[str, str]
    ) -> PipelineExecution:
        """Trigger deployment pipeline."""
        
        execution = PipelineExecution(
            pipeline_id=f"deploy-{sprint_id}-{environment.value}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            provider=PipelineProvider.GITHUB_ACTIONS,
            environment=environment,
            sprint_id=sprint_id
        )
        
        execution.status = PipelineStatus.RUNNING
        execution.started_at = datetime.now()
        
        # Simulate deployment process
        await self._simulate_deployment(execution, artifacts)
        
        return execution
    
    async def _simulate_deployment(self, execution: PipelineExecution, artifacts: Dict[str, str]):
        """Simulate deployment process."""
        
        steps = [
            "Building application...",
            "Running pre-deployment tests...",
            "Backing up current deployment...",
            "Deploying new version...",
            "Running smoke tests...",
            "Updating load balancer...",
            "Deployment completed successfully!"
        ]
        
        for step in steps:
            execution.logs.append(f"[{datetime.now().isoformat()}] {step}")
            await asyncio.sleep(0.1)  # Simulate processing time
        
        execution.status = PipelineStatus.SUCCESS
        execution.completed_at = datetime.now()
        execution.artifacts = artifacts
        execution.metrics = {
            "deployment_time_seconds": 45,
            "build_size_mb": 23.4,
            "test_coverage_percent": 87.3
        }


class CICDPipelineManager:
    """Manages CI/CD pipeline integration for Gaggle sprints."""
    
    def __init__(self):
        self.logger = get_logger("cicd_manager")
        self.configurations: Dict[str, PipelineConfiguration] = {}
        self.executions: Dict[str, PipelineExecution] = {}
        
        # Initialize pipeline providers
        self.github_actions = GitHubActionsPipeline()
    
    def configure_pipeline(
        self,
        project_id: str,
        configuration: PipelineConfiguration
    ):
        """Configure CI/CD pipeline for a project."""
        
        self.configurations[project_id] = configuration
        
        self.logger.info(
            "pipeline_configured",
            project_id=project_id,
            provider=configuration.provider.value,
            environments=[env.value for env in configuration.environments],
            auto_deploy=configuration.auto_deploy_on_sprint_completion
        )
    
    async def setup_sprint_pipeline(self, sprint: Sprint) -> Dict[str, Any]:
        """Set up CI/CD pipeline for a sprint."""
        
        project_id = getattr(sprint, 'project_id', 'default')
        config = self.configurations.get(project_id)
        
        if not config:
            raise ValueError(f"No pipeline configuration found for project {project_id}")
        
        setup_results = {
            "sprint_id": sprint.id,
            "provider": config.provider.value,
            "workflows_created": [],
            "environments_configured": [],
            "quality_gates": config.quality_gates
        }
        
        # Create workflows based on provider
        if config.provider == PipelineProvider.GITHUB_ACTIONS:
            workflow_path = await self.github_actions.create_sprint_workflow(sprint)
            setup_results["workflows_created"].append(workflow_path)
        
        # Configure environments
        for environment in config.environments:
            env_config = await self._configure_environment(environment, sprint)
            setup_results["environments_configured"].append({
                "environment": environment.value,
                "configuration": env_config
            })
        
        self.logger.info(
            "sprint_pipeline_setup_completed",
            sprint_id=sprint.id,
            workflows_count=len(setup_results["workflows_created"]),
            environments_count=len(setup_results["environments_configured"])
        )
        
        return setup_results
    
    async def _configure_environment(
        self,
        environment: DeploymentEnvironment,
        sprint: Sprint
    ) -> Dict[str, Any]:
        """Configure deployment environment for sprint."""
        
        config = {
            "environment": environment.value,
            "deployment_strategy": "blue_green" if environment == DeploymentEnvironment.PRODUCTION else "rolling",
            "auto_rollback": True,
            "health_checks": [
                {"endpoint": "/health", "timeout": 30},
                {"endpoint": "/ready", "timeout": 10}
            ],
            "monitoring": {
                "metrics_retention_days": 30,
                "alert_thresholds": {
                    "error_rate_percent": 1.0,
                    "response_time_ms": 500,
                    "cpu_usage_percent": 80,
                    "memory_usage_percent": 85
                }
            }
        }
        
        return config
    
    async def execute_deployment_pipeline(
        self,
        sprint: Sprint,
        environment: DeploymentEnvironment,
        user_story_id: Optional[str] = None
    ) -> PipelineExecution:
        """Execute deployment pipeline for sprint or user story."""
        
        project_id = getattr(sprint, 'project_id', 'default')
        config = self.configurations.get(project_id)
        
        if not config:
            raise ValueError(f"No pipeline configuration found for project {project_id}")
        
        # Prepare deployment artifacts
        artifacts = await self._prepare_deployment_artifacts(sprint, user_story_id)
        
        # Execute pipeline based on provider
        if config.provider == PipelineProvider.GITHUB_ACTIONS:
            execution = await self.github_actions.trigger_deployment(
                environment=environment,
                sprint_id=sprint.id,
                artifacts=artifacts
            )
        else:
            raise ValueError(f"Unsupported pipeline provider: {config.provider}")
        
        # Store execution for tracking
        self.executions[execution.pipeline_id] = execution
        
        self.logger.info(
            "deployment_pipeline_executed",
            pipeline_id=execution.pipeline_id,
            sprint_id=sprint.id,
            environment=environment.value,
            status=execution.status.value
        )
        
        return execution
    
    async def _prepare_deployment_artifacts(
        self,
        sprint: Sprint,
        user_story_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Prepare deployment artifacts for sprint or user story."""
        
        artifacts = {
            "application_bundle": f"gaggle-app-{sprint.id}.tar.gz",
            "database_migrations": f"migrations-{sprint.id}.sql",
            "configuration": f"config-{sprint.id}.env",
            "documentation": f"docs-{sprint.id}.pdf"
        }
        
        if user_story_id:
            artifacts["feature_config"] = f"feature-{user_story_id}.json"
        
        return artifacts
    
    async def monitor_pipeline_execution(
        self,
        pipeline_id: str
    ) -> Dict[str, Any]:
        """Monitor pipeline execution status and metrics."""
        
        execution = self.executions.get(pipeline_id)
        
        if not execution:
            raise ValueError(f"Pipeline execution {pipeline_id} not found")
        
        # Calculate execution metrics
        duration_seconds = 0
        if execution.started_at and execution.completed_at:
            duration_seconds = (execution.completed_at - execution.started_at).total_seconds()
        elif execution.started_at:
            duration_seconds = (datetime.now() - execution.started_at).total_seconds()
        
        monitoring_data = {
            "pipeline_id": pipeline_id,
            "status": execution.status.value,
            "duration_seconds": duration_seconds,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "logs_count": len(execution.logs),
            "artifacts_count": len(execution.artifacts),
            "metrics": execution.metrics,
            "environment": execution.environment.value
        }
        
        return monitoring_data
    
    async def handle_sprint_completion(self, sprint: Sprint) -> List[PipelineExecution]:
        """Handle sprint completion with automatic deployment."""
        
        project_id = getattr(sprint, 'project_id', 'default')
        config = self.configurations.get(project_id)
        
        if not config or not config.auto_deploy_on_sprint_completion:
            return []
        
        executions = []
        
        # Deploy to staging first
        if DeploymentEnvironment.STAGING in config.environments:
            staging_execution = await self.execute_deployment_pipeline(
                sprint=sprint,
                environment=DeploymentEnvironment.STAGING
            )
            executions.append(staging_execution)
            
            # Wait for staging deployment to complete
            while staging_execution.status == PipelineStatus.RUNNING:
                await asyncio.sleep(1)
                monitoring_data = await self.monitor_pipeline_execution(staging_execution.pipeline_id)
                staging_execution.status = PipelineStatus(monitoring_data["status"])
        
        # Deploy to production if staging succeeded
        if (DeploymentEnvironment.PRODUCTION in config.environments and 
            staging_execution.status == PipelineStatus.SUCCESS):
            
            production_execution = await self.execute_deployment_pipeline(
                sprint=sprint,
                environment=DeploymentEnvironment.PRODUCTION
            )
            executions.append(production_execution)
        
        self.logger.info(
            "sprint_completion_deployments_triggered",
            sprint_id=sprint.id,
            deployment_count=len(executions),
            environments=[exec.environment.value for exec in executions]
        )
        
        return executions
    
    async def get_pipeline_metrics(
        self,
        sprint_id: Optional[str] = None,
        environment: Optional[DeploymentEnvironment] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """Get CI/CD pipeline metrics."""
        
        cutoff_date = datetime.now() - timedelta(days=time_range_days)
        relevant_executions = []
        
        for execution in self.executions.values():
            if execution.started_at and execution.started_at >= cutoff_date:
                if sprint_id and execution.sprint_id != sprint_id:
                    continue
                if environment and execution.environment != environment:
                    continue
                relevant_executions.append(execution)
        
        total_executions = len(relevant_executions)
        successful_executions = len([e for e in relevant_executions if e.status == PipelineStatus.SUCCESS])
        failed_executions = len([e for e in relevant_executions if e.status == PipelineStatus.FAILURE])
        
        avg_duration = 0
        if relevant_executions:
            durations = []
            for execution in relevant_executions:
                if execution.started_at and execution.completed_at:
                    durations.append((execution.completed_at - execution.started_at).total_seconds())
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        metrics = {
            "summary": {
                "total_executions": total_executions,
                "success_rate_percent": (successful_executions / total_executions * 100) if total_executions > 0 else 0,
                "failure_rate_percent": (failed_executions / total_executions * 100) if total_executions > 0 else 0,
                "average_duration_seconds": avg_duration
            },
            "by_environment": {},
            "by_status": {
                "successful": successful_executions,
                "failed": failed_executions,
                "pending": len([e for e in relevant_executions if e.status == PipelineStatus.PENDING]),
                "running": len([e for e in relevant_executions if e.status == PipelineStatus.RUNNING])
            },
            "time_range_days": time_range_days
        }
        
        # Metrics by environment
        for env in DeploymentEnvironment:
            env_executions = [e for e in relevant_executions if e.environment == env]
            if env_executions:
                env_successful = len([e for e in env_executions if e.status == PipelineStatus.SUCCESS])
                metrics["by_environment"][env.value] = {
                    "total": len(env_executions),
                    "successful": env_successful,
                    "success_rate_percent": (env_successful / len(env_executions) * 100)
                }
        
        return metrics


# Global CI/CD manager instance
cicd_manager = CICDPipelineManager()