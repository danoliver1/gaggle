"""CI/CD pipeline integration for automated sprint execution."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging
import json

from ...models.core import Sprint, Task, UserStory, AgentRole
from ...models.enums import TaskStatus, TaskPriority
from ..coordination.quality_gates import QualityGateManager, QualityGateStatus

logger = logging.getLogger(__name__)


class PipelineStageType(Enum):
    """Types of pipeline stages."""
    SOURCE_CONTROL = "source_control"
    BUILD = "build"
    TEST = "test"
    QUALITY_GATE = "quality_gate"
    SECURITY_SCAN = "security_scan"
    DEPLOY_STAGING = "deploy_staging"
    INTEGRATION_TEST = "integration_test"
    DEPLOY_PRODUCTION = "deploy_production"
    MONITORING_SETUP = "monitoring_setup"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class DeploymentStrategy(Enum):
    """Deployment strategies."""
    BLUE_GREEN = "blue_green"
    ROLLING = "rolling"
    CANARY = "canary"
    FEATURE_FLAG = "feature_flag"


@dataclass
class PipelineStage:
    """Configuration for a pipeline stage."""
    stage_type: PipelineStageType
    name: str
    description: str
    
    # Execution
    command: str
    timeout_minutes: int = 30
    retry_count: int = 0
    
    # Dependencies
    depends_on: List[PipelineStageType] = field(default_factory=list)
    
    # Conditions
    run_condition: Optional[str] = None  # Expression to evaluate
    failure_action: str = "stop"  # stop, continue, manual
    
    # Artifacts
    input_artifacts: List[str] = field(default_factory=list)
    output_artifacts: List[str] = field(default_factory=list)
    
    # Environment
    environment_vars: Dict[str, str] = field(default_factory=dict)
    
    # Custom execution
    custom_executor: Optional[Callable] = None


@dataclass
class StageExecution:
    """Execution result for a pipeline stage."""
    stage: PipelineStage
    status: PipelineStatus
    
    # Timing
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Results
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    artifacts: List[str] = field(default_factory=list)
    
    # Metadata
    executor_info: Dict[str, Any] = field(default_factory=dict)
    resource_usage: Dict[str, float] = field(default_factory=dict)


@dataclass
class PipelineExecution:
    """Complete pipeline execution tracking."""
    execution_id: str
    sprint_id: str
    pipeline_config: 'PipelineConfig'
    
    # Status
    status: PipelineStatus = PipelineStatus.PENDING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Stages
    stage_executions: Dict[PipelineStageType, StageExecution] = field(default_factory=dict)
    
    # Results
    success_count: int = 0
    failure_count: int = 0
    total_duration_minutes: float = 0.0
    
    # Context
    trigger_event: str = ""
    triggered_by: str = ""
    environment: str = "development"
    
    def add_stage_result(self, execution: StageExecution) -> None:
        """Add stage execution result."""
        self.stage_executions[execution.stage.stage_type] = execution
        
        if execution.status == PipelineStatus.SUCCESS:
            self.success_count += 1
        elif execution.status == PipelineStatus.FAILED:
            self.failure_count += 1
    
    def get_overall_status(self) -> PipelineStatus:
        """Get overall pipeline status."""
        if not self.stage_executions:
            return PipelineStatus.PENDING
            
        statuses = [exec.status for exec in self.stage_executions.values()]
        
        if PipelineStatus.RUNNING in statuses:
            return PipelineStatus.RUNNING
        elif PipelineStatus.FAILED in statuses:
            return PipelineStatus.FAILED
        elif all(status == PipelineStatus.SUCCESS for status in statuses):
            return PipelineStatus.SUCCESS
        else:
            return PipelineStatus.RUNNING


@dataclass
class PipelineConfig:
    """Configuration for a complete CI/CD pipeline."""
    name: str
    description: str
    version: str = "1.0"
    
    # Stages
    stages: List[PipelineStage] = field(default_factory=list)
    
    # Triggers
    triggers: List[str] = field(default_factory=list)  # push, pull_request, sprint_start, etc.
    
    # Environment
    target_environments: List[str] = field(default_factory=lambda: ["staging", "production"])
    deployment_strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    
    # Quality gates
    quality_gate_required: bool = True
    quality_gate_threshold: float = 0.8  # Minimum quality score
    
    # Notifications
    notification_channels: List[str] = field(default_factory=list)
    
    # Rollback
    auto_rollback_enabled: bool = True
    rollback_conditions: List[str] = field(default_factory=list)
    
    def get_stage_by_type(self, stage_type: PipelineStageType) -> Optional[PipelineStage]:
        """Get stage by type."""
        return next((stage for stage in self.stages if stage.stage_type == stage_type), None)


class PipelineManager:
    """Manages CI/CD pipeline execution for sprint workflows."""
    
    def __init__(self):
        self.pipeline_configs: Dict[str, PipelineConfig] = {}
        self.active_executions: Dict[str, PipelineExecution] = {}
        self.quality_gate_manager = QualityGateManager()
        self.quality_gate_manager.configure_standard_gates()
        
    def register_pipeline(self, config: PipelineConfig) -> None:
        """Register a pipeline configuration."""
        self.pipeline_configs[config.name] = config
        logger.info(f"Registered pipeline: {config.name}")
    
    def configure_standard_pipelines(self) -> None:
        """Configure standard CI/CD pipelines for Gaggle sprints."""
        
        # Sprint Development Pipeline
        sprint_pipeline = self._create_sprint_pipeline()
        self.register_pipeline(sprint_pipeline)
        
        # Feature Branch Pipeline  
        feature_pipeline = self._create_feature_pipeline()
        self.register_pipeline(feature_pipeline)
        
        # Release Pipeline
        release_pipeline = self._create_release_pipeline()
        self.register_pipeline(release_pipeline)
    
    def _create_sprint_pipeline(self) -> PipelineConfig:
        """Create pipeline for sprint execution."""
        stages = [
            PipelineStage(
                stage_type=PipelineStageType.SOURCE_CONTROL,
                name="Checkout Source",
                description="Checkout source code and sprint configuration",
                command="git checkout sprint-branch",
                timeout_minutes=5
            ),
            PipelineStage(
                stage_type=PipelineStageType.BUILD,
                name="Build Sprint",
                description="Build all sprint components",
                command="uv sync && uv run python -m gaggle.build",
                timeout_minutes=15,
                depends_on=[PipelineStageType.SOURCE_CONTROL]
            ),
            PipelineStage(
                stage_type=PipelineStageType.TEST,
                name="Test Sprint",
                description="Run all sprint tests",
                command="uv run pytest tests/ --cov=src/gaggle",
                timeout_minutes=30,
                depends_on=[PipelineStageType.BUILD]
            ),
            PipelineStage(
                stage_type=PipelineStageType.QUALITY_GATE,
                name="Quality Gate",
                description="Execute quality gates for sprint deliverables",
                command="quality_gate_check",
                timeout_minutes=20,
                depends_on=[PipelineStageType.TEST],
                custom_executor=self._execute_quality_gate
            ),
            PipelineStage(
                stage_type=PipelineStageType.SECURITY_SCAN,
                name="Security Scan",
                description="Security vulnerability scanning",
                command="uv run safety check && uv run bandit -r src/",
                timeout_minutes=10,
                depends_on=[PipelineStageType.QUALITY_GATE]
            ),
            PipelineStage(
                stage_type=PipelineStageType.DEPLOY_STAGING,
                name="Deploy to Staging",
                description="Deploy sprint deliverables to staging",
                command="deploy_to_staging.sh",
                timeout_minutes=15,
                depends_on=[PipelineStageType.SECURITY_SCAN]
            ),
            PipelineStage(
                stage_type=PipelineStageType.INTEGRATION_TEST,
                name="Integration Tests",
                description="Run integration tests in staging",
                command="uv run pytest tests/integration/ --env=staging",
                timeout_minutes=25,
                depends_on=[PipelineStageType.DEPLOY_STAGING]
            )
        ]
        
        return PipelineConfig(
            name="sprint_pipeline",
            description="Complete pipeline for sprint execution and delivery",
            stages=stages,
            triggers=["sprint_start", "sprint_commit"],
            quality_gate_required=True,
            quality_gate_threshold=0.85,
            auto_rollback_enabled=True
        )
    
    def _create_feature_pipeline(self) -> PipelineConfig:
        """Create pipeline for individual feature development."""
        stages = [
            PipelineStage(
                stage_type=PipelineStageType.SOURCE_CONTROL,
                name="Checkout Feature",
                description="Checkout feature branch",
                command="git checkout feature-branch",
                timeout_minutes=5
            ),
            PipelineStage(
                stage_type=PipelineStageType.BUILD,
                name="Build Feature",
                description="Build feature components",
                command="uv sync && uv run python -m gaggle.build_feature",
                timeout_minutes=10,
                depends_on=[PipelineStageType.SOURCE_CONTROL]
            ),
            PipelineStage(
                stage_type=PipelineStageType.TEST,
                name="Test Feature",
                description="Run feature tests",
                command="uv run pytest tests/features/ -k feature_name",
                timeout_minutes=20,
                depends_on=[PipelineStageType.BUILD]
            ),
            PipelineStage(
                stage_type=PipelineStageType.QUALITY_GATE,
                name="Feature Quality Gate",
                description="Quality gate for feature",
                command="feature_quality_check",
                timeout_minutes=15,
                depends_on=[PipelineStageType.TEST],
                custom_executor=self._execute_quality_gate
            )
        ]
        
        return PipelineConfig(
            name="feature_pipeline",
            description="Pipeline for individual feature development",
            stages=stages,
            triggers=["pull_request", "feature_commit"],
            quality_gate_required=True,
            quality_gate_threshold=0.80
        )
    
    def _create_release_pipeline(self) -> PipelineConfig:
        """Create pipeline for production release."""
        stages = [
            PipelineStage(
                stage_type=PipelineStageType.SOURCE_CONTROL,
                name="Checkout Release",
                description="Checkout release branch",
                command="git checkout release-branch",
                timeout_minutes=5
            ),
            PipelineStage(
                stage_type=PipelineStageType.BUILD,
                name="Build Release",
                description="Build production release",
                command="uv sync --no-dev && uv run python -m gaggle.build_release",
                timeout_minutes=20,
                depends_on=[PipelineStageType.SOURCE_CONTROL]
            ),
            PipelineStage(
                stage_type=PipelineStageType.TEST,
                name="Full Test Suite",
                description="Run complete test suite",
                command="uv run pytest tests/ --cov=src/gaggle --cov-fail-under=85",
                timeout_minutes=45,
                depends_on=[PipelineStageType.BUILD]
            ),
            PipelineStage(
                stage_type=PipelineStageType.SECURITY_SCAN,
                name="Security Audit",
                description="Complete security audit",
                command="uv run safety check && uv run bandit -r src/ -ll",
                timeout_minutes=15,
                depends_on=[PipelineStageType.TEST]
            ),
            PipelineStage(
                stage_type=PipelineStageType.DEPLOY_PRODUCTION,
                name="Deploy to Production",
                description="Deploy to production environment",
                command="deploy_to_production.sh",
                timeout_minutes=30,
                depends_on=[PipelineStageType.SECURITY_SCAN]
            ),
            PipelineStage(
                stage_type=PipelineStageType.MONITORING_SETUP,
                name="Setup Monitoring",
                description="Configure production monitoring",
                command="setup_monitoring.sh",
                timeout_minutes=10,
                depends_on=[PipelineStageType.DEPLOY_PRODUCTION]
            )
        ]
        
        return PipelineConfig(
            name="release_pipeline",
            description="Production release pipeline with full validation",
            stages=stages,
            triggers=["release_tag"],
            target_environments=["production"],
            deployment_strategy=DeploymentStrategy.BLUE_GREEN,
            quality_gate_required=True,
            quality_gate_threshold=0.90,
            auto_rollback_enabled=True
        )
    
    async def execute_pipeline(
        self, 
        pipeline_name: str,
        context: Dict[str, Any],
        trigger_event: str = "manual"
    ) -> PipelineExecution:
        """Execute a complete pipeline."""
        if pipeline_name not in self.pipeline_configs:
            raise ValueError(f"Pipeline not found: {pipeline_name}")
            
        config = self.pipeline_configs[pipeline_name]
        execution_id = f"{pipeline_name}_{datetime.now().isoformat()}"
        
        execution = PipelineExecution(
            execution_id=execution_id,
            sprint_id=context.get('sprint_id', ''),
            pipeline_config=config,
            trigger_event=trigger_event,
            triggered_by=context.get('triggered_by', 'system'),
            environment=context.get('environment', 'development')
        )
        
        self.active_executions[execution_id] = execution
        logger.info(f"Starting pipeline execution: {execution_id}")
        
        try:
            execution.status = PipelineStatus.RUNNING
            
            # Execute stages in dependency order
            execution_order = self._get_stage_execution_order(config.stages)
            
            for stage in execution_order:
                if await self._should_execute_stage(stage, execution, context):
                    stage_result = await self._execute_stage(stage, execution, context)
                    execution.add_stage_result(stage_result)
                    
                    if stage_result.status == PipelineStatus.FAILED and stage.failure_action == "stop":
                        execution.status = PipelineStatus.FAILED
                        break
                else:
                    # Create skipped stage result
                    skipped_result = StageExecution(
                        stage=stage,
                        status=PipelineStatus.SKIPPED,
                        started_at=datetime.now(),
                        completed_at=datetime.now()
                    )
                    execution.add_stage_result(skipped_result)
            
            # Determine final status
            execution.status = execution.get_overall_status()
            execution.completed_at = datetime.now()
            execution.total_duration_minutes = (
                execution.completed_at - execution.started_at
            ).total_seconds() / 60.0
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            execution.status = PipelineStatus.FAILED
            execution.completed_at = datetime.now()
        
        logger.info(f"Pipeline execution completed: {execution_id} - {execution.status.value}")
        return execution
    
    async def _execute_stage(
        self, 
        stage: PipelineStage, 
        execution: PipelineExecution, 
        context: Dict[str, Any]
    ) -> StageExecution:
        """Execute a single pipeline stage."""
        logger.info(f"Executing stage: {stage.name}")
        start_time = datetime.now()
        
        stage_exec = StageExecution(
            stage=stage,
            status=PipelineStatus.RUNNING,
            started_at=start_time
        )
        
        try:
            if stage.custom_executor:
                # Use custom executor
                result = await stage.custom_executor(stage, execution, context)
                stage_exec.stdout = result.get('output', '')
                stage_exec.exit_code = result.get('exit_code', 0)
                stage_exec.artifacts = result.get('artifacts', [])
            else:
                # Execute command
                result = await self._execute_command(
                    stage.command, 
                    stage.timeout_minutes * 60,
                    stage.environment_vars
                )
                stage_exec.stdout = result['stdout']
                stage_exec.stderr = result['stderr']
                stage_exec.exit_code = result['exit_code']
            
            # Determine status
            if stage_exec.exit_code == 0:
                stage_exec.status = PipelineStatus.SUCCESS
            else:
                stage_exec.status = PipelineStatus.FAILED
                
        except asyncio.TimeoutError:
            stage_exec.status = PipelineStatus.FAILED
            stage_exec.stderr = f"Stage timed out after {stage.timeout_minutes} minutes"
        except Exception as e:
            stage_exec.status = PipelineStatus.FAILED
            stage_exec.stderr = str(e)
        
        stage_exec.completed_at = datetime.now()
        stage_exec.duration_seconds = (
            stage_exec.completed_at - stage_exec.started_at
        ).total_seconds()
        
        return stage_exec
    
    async def _execute_quality_gate(
        self, 
        stage: PipelineStage, 
        execution: PipelineExecution, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Custom executor for quality gate stages."""
        # Mock task for quality gate execution
        mock_task = Task(
            id=f"qg_task_{execution.execution_id}",
            title="Quality Gate Validation",
            description="Validate sprint deliverables against quality criteria",
            estimated_effort=1,
            status=TaskStatus.IN_PROGRESS
        )
        
        # Execute quality gates
        gate_result = await self.quality_gate_manager.execute_quality_gates(
            mock_task, context
        )
        
        # Determine success based on quality gate results
        success = gate_result['overall_status'] in [
            QualityGateStatus.PASSED, 
            QualityGateStatus.CONDITIONAL_PASS
        ]
        
        return {
            'exit_code': 0 if success else 1,
            'output': json.dumps(gate_result, default=str),
            'artifacts': ['quality_gate_report.json']
        }
    
    async def _execute_command(
        self, 
        command: str, 
        timeout_seconds: int,
        env_vars: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """Execute a shell command with timeout."""
        # Mock command execution for development
        await asyncio.sleep(0.1)  # Simulate execution time
        
        # Simulate successful execution
        return {
            'exit_code': 0,
            'stdout': f"Mock execution of: {command}",
            'stderr': ''
        }
    
    def _get_stage_execution_order(self, stages: List[PipelineStage]) -> List[PipelineStage]:
        """Get stages in execution order based on dependencies."""
        ordered_stages = []
        remaining_stages = stages.copy()
        
        while remaining_stages:
            # Find stages with satisfied dependencies
            ready_stages = []
            for stage in remaining_stages:
                dependencies_satisfied = all(
                    any(completed.stage_type == dep for completed in ordered_stages)
                    for dep in stage.depends_on
                )
                if dependencies_satisfied:
                    ready_stages.append(stage)
            
            if not ready_stages:
                # Handle circular dependencies or add stages without dependencies
                ready_stages = [
                    stage for stage in remaining_stages 
                    if not stage.depends_on
                ]
                if not ready_stages:
                    ready_stages = remaining_stages[:1]  # Force progress
            
            # Add ready stages to execution order
            for stage in ready_stages:
                ordered_stages.append(stage)
                remaining_stages.remove(stage)
        
        return ordered_stages
    
    async def _should_execute_stage(
        self, 
        stage: PipelineStage, 
        execution: PipelineExecution, 
        context: Dict[str, Any]
    ) -> bool:
        """Determine if a stage should be executed based on conditions."""
        if not stage.run_condition:
            return True
            
        # Simple condition evaluation (in production, use a proper expression evaluator)
        if stage.run_condition == "production_only":
            return execution.environment == "production"
        elif stage.run_condition == "quality_gate_passed":
            return execution.success_count > execution.failure_count
        
        return True
    
    def get_pipeline_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a pipeline execution."""
        if execution_id not in self.active_executions:
            return None
            
        execution = self.active_executions[execution_id]
        
        return {
            'execution_id': execution_id,
            'status': execution.status.value,
            'progress': len(execution.stage_executions) / len(execution.pipeline_config.stages) * 100,
            'stages': {
                stage_type.value: {
                    'status': exec.status.value,
                    'duration_seconds': exec.duration_seconds
                }
                for stage_type, exec in execution.stage_executions.items()
            },
            'total_duration_minutes': execution.total_duration_minutes
        }
    
    def get_pipeline_metrics(self, lookback_days: int = 30) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        # Filter recent executions
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        recent_executions = [
            exec for exec in self.active_executions.values()
            if exec.started_at >= cutoff_date and exec.completed_at
        ]
        
        if not recent_executions:
            return {'status': 'no_data'}
        
        # Calculate metrics
        success_rate = len([e for e in recent_executions if e.status == PipelineStatus.SUCCESS]) / len(recent_executions)
        avg_duration = sum(e.total_duration_minutes for e in recent_executions) / len(recent_executions)
        
        return {
            'total_executions': len(recent_executions),
            'success_rate': success_rate * 100,
            'average_duration_minutes': avg_duration,
            'pipeline_breakdown': {
                pipeline: len([e for e in recent_executions if e.pipeline_config.name == pipeline])
                for pipeline in self.pipeline_configs.keys()
            }
        }