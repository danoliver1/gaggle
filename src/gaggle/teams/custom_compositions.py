"""Custom team composition system for different project types and requirements."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from ..config.models import AgentRole, ModelTier
from ..utils.logging import get_logger

logger = structlog.get_logger(__name__)


class ProjectType(str, Enum):
    """Types of software projects."""

    WEB_APPLICATION = "web_application"
    MOBILE_APP = "mobile_app"
    API_SERVICE = "api_service"
    MICROSERVICES = "microservices"
    DATA_PIPELINE = "data_pipeline"
    ML_PROJECT = "ml_project"
    DEVOPS_INFRASTRUCTURE = "devops_infrastructure"
    FRONTEND_ONLY = "frontend_only"
    BACKEND_ONLY = "backend_only"
    FULL_STACK = "full_stack"


class TeamSize(str, Enum):
    """Team size categories."""

    SMALL = "small"  # 3-5 agents
    MEDIUM = "medium"  # 6-8 agents
    LARGE = "large"  # 9-12 agents
    ENTERPRISE = "enterprise"  # 13+ agents


class ProjectComplexity(str, Enum):
    """Project complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


@dataclass
class TeamCompositionRequirements:
    """Requirements for team composition."""

    project_type: ProjectType
    team_size: TeamSize
    complexity: ProjectComplexity
    budget_constraints: float | None = None
    timeline_weeks: int | None = None
    specific_skills: list[str] = None
    quality_requirements: list[str] = None
    performance_requirements: dict[str, Any] = None
    compliance_requirements: list[str] = None


@dataclass
class AgentSpecification:
    """Specification for an agent in the team."""

    role: AgentRole
    name: str
    specialization: str | None = None
    model_tier: ModelTier = None
    skills: list[str] = None
    capacity_percentage: float = 100.0  # How much of this agent's time is allocated
    cost_weight: float = 1.0


@dataclass
class TeamComposition:
    """Complete team composition with agents and configuration."""

    composition_id: str
    name: str
    description: str
    project_type: ProjectType
    agents: list[AgentSpecification]
    estimated_cost_per_sprint: float
    estimated_velocity: float
    strengths: list[str]
    limitations: list[str]
    success_metrics: list[str]
    created_at: datetime


class TeamCompositionBuilder:
    """Builds custom team compositions based on requirements."""

    def __init__(self):
        self.logger = get_logger("team_composition_builder")

        # Cost per sprint for different model tiers (simplified)
        self.tier_costs = {
            ModelTier.HAIKU: 50.0,  # Coordination agents
            ModelTier.SONNET: 150.0,  # Implementation agents
            ModelTier.OPUS: 300.0,  # Architecture agents
        }

    async def build_team_composition(
        self, requirements: TeamCompositionRequirements
    ) -> TeamComposition:
        """Build a custom team composition based on requirements."""

        self.logger.info(
            "building_team_composition",
            project_type=requirements.project_type.value,
            team_size=requirements.team_size.value,
            complexity=requirements.complexity.value,
        )

        # Determine base team structure
        base_agents = self._get_base_team_structure(requirements)

        # Add specialized agents based on project type
        specialized_agents = self._add_specialized_agents(requirements, base_agents)

        # Optimize team for budget and constraints
        optimized_agents = self._optimize_team_composition(
            specialized_agents, requirements
        )

        # Calculate team metrics
        composition = self._finalize_composition(optimized_agents, requirements)

        self.logger.info(
            "team_composition_built",
            composition_id=composition.composition_id,
            agent_count=len(composition.agents),
            estimated_cost=composition.estimated_cost_per_sprint,
        )

        return composition

    def _get_base_team_structure(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get base team structure for any project."""

        base_agents = []

        # Always include coordination layer
        base_agents.append(
            AgentSpecification(
                role=AgentRole.PRODUCT_OWNER,
                name="ProductOwner",
                model_tier=ModelTier.HAIKU,
                skills=[
                    "requirements_analysis",
                    "stakeholder_management",
                    "prioritization",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        base_agents.append(
            AgentSpecification(
                role=AgentRole.SCRUM_MASTER,
                name="ScrumMaster",
                model_tier=ModelTier.HAIKU,
                skills=[
                    "agile_facilitation",
                    "team_coordination",
                    "blocker_resolution",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Always include tech lead for architecture
        base_agents.append(
            AgentSpecification(
                role=AgentRole.TECH_LEAD,
                name="TechLead",
                model_tier=ModelTier.OPUS,
                skills=["architecture_design", "code_review", "technical_decisions"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Add QA for quality assurance
        if requirements.complexity != ProjectComplexity.SIMPLE:
            base_agents.append(
                AgentSpecification(
                    role=AgentRole.QA_ENGINEER,
                    name="QAEngineer",
                    model_tier=ModelTier.SONNET,
                    skills=["testing", "quality_assurance", "automation"],
                    capacity_percentage=100.0,
                    cost_weight=1.0,
                )
            )

        return base_agents

    def _add_specialized_agents(
        self,
        requirements: TeamCompositionRequirements,
        base_agents: list[AgentSpecification],
    ) -> list[AgentSpecification]:
        """Add specialized agents based on project type."""

        agents = base_agents.copy()

        if requirements.project_type == ProjectType.WEB_APPLICATION:
            agents.extend(self._get_web_app_specialists(requirements))

        elif requirements.project_type == ProjectType.MOBILE_APP:
            agents.extend(self._get_mobile_app_specialists(requirements))

        elif requirements.project_type == ProjectType.API_SERVICE:
            agents.extend(self._get_api_service_specialists(requirements))

        elif requirements.project_type == ProjectType.MICROSERVICES:
            agents.extend(self._get_microservices_specialists(requirements))

        elif requirements.project_type == ProjectType.DATA_PIPELINE:
            agents.extend(self._get_data_pipeline_specialists(requirements))

        elif requirements.project_type == ProjectType.ML_PROJECT:
            agents.extend(self._get_ml_project_specialists(requirements))

        elif requirements.project_type == ProjectType.DEVOPS_INFRASTRUCTURE:
            agents.extend(self._get_devops_specialists(requirements))

        elif requirements.project_type == ProjectType.FRONTEND_ONLY:
            agents.extend(self._get_frontend_specialists(requirements))

        elif requirements.project_type == ProjectType.BACKEND_ONLY:
            agents.extend(self._get_backend_specialists(requirements))

        elif requirements.project_type == ProjectType.FULL_STACK:
            agents.extend(self._get_fullstack_specialists(requirements))

        return agents

    def _get_web_app_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for web application projects."""

        specialists = []

        # Frontend developers
        specialists.append(
            AgentSpecification(
                role=AgentRole.FRONTEND_DEV,
                name="FrontendDev-UI",
                specialization="user_interface",
                model_tier=ModelTier.SONNET,
                skills=["react", "typescript", "responsive_design", "accessibility"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Backend developers
        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-API",
                specialization="api_development",
                model_tier=ModelTier.SONNET,
                skills=["fastapi", "postgresql", "authentication", "rest_apis"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Add fullstack for integration
        if requirements.team_size in [
            TeamSize.MEDIUM,
            TeamSize.LARGE,
            TeamSize.ENTERPRISE,
        ]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.FULLSTACK_DEV,
                    name="FullstackDev-Integration",
                    specialization="system_integration",
                    model_tier=ModelTier.SONNET,
                    skills=["end_to_end_development", "deployment", "devops"],
                    capacity_percentage=100.0,
                    cost_weight=1.0,
                )
            )

        # Add additional specialists for larger teams
        if requirements.team_size in [TeamSize.LARGE, TeamSize.ENTERPRISE]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.FRONTEND_DEV,
                    name="FrontendDev-Performance",
                    specialization="performance_optimization",
                    model_tier=ModelTier.SONNET,
                    skills=[
                        "performance_optimization",
                        "bundle_optimization",
                        "caching",
                    ],
                    capacity_percentage=75.0,
                    cost_weight=0.75,
                )
            )

        return specialists

    def _get_mobile_app_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for mobile app projects."""

        specialists = []

        # Mobile frontend developers
        specialists.append(
            AgentSpecification(
                role=AgentRole.FRONTEND_DEV,
                name="MobileDev-iOS",
                specialization="ios_development",
                model_tier=ModelTier.SONNET,
                skills=["swift", "ios_sdk", "app_store", "mobile_ui"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.FRONTEND_DEV,
                name="MobileDev-Android",
                specialization="android_development",
                model_tier=ModelTier.SONNET,
                skills=["kotlin", "android_sdk", "play_store", "material_design"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Backend for mobile API
        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-Mobile-API",
                specialization="mobile_backend",
                model_tier=ModelTier.SONNET,
                skills=[
                    "mobile_apis",
                    "push_notifications",
                    "offline_sync",
                    "security",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        return specialists

    def _get_api_service_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for API service projects."""

        specialists = []

        # API developers
        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-API-Core",
                specialization="api_development",
                model_tier=ModelTier.SONNET,
                skills=["rest_apis", "graphql", "openapi", "api_security"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-Data",
                specialization="data_layer",
                model_tier=ModelTier.SONNET,
                skills=["database_design", "query_optimization", "data_modeling"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # DevOps for deployment
        if requirements.team_size in [
            TeamSize.MEDIUM,
            TeamSize.LARGE,
            TeamSize.ENTERPRISE,
        ]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.FULLSTACK_DEV,
                    name="DevOpsDev",
                    specialization="infrastructure",
                    model_tier=ModelTier.SONNET,
                    skills=["docker", "kubernetes", "ci_cd", "monitoring"],
                    capacity_percentage=75.0,
                    cost_weight=0.75,
                )
            )

        return specialists

    def _get_microservices_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for microservices projects."""

        specialists = []

        # Multiple backend developers for different services
        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-Service-A",
                specialization="user_service",
                model_tier=ModelTier.SONNET,
                skills=["microservices", "authentication", "user_management"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-Service-B",
                specialization="business_service",
                model_tier=ModelTier.SONNET,
                skills=["business_logic", "event_driven", "message_queues"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # Fullstack for service integration
        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="FullstackDev-Integration",
                specialization="service_integration",
                model_tier=ModelTier.SONNET,
                skills=["service_mesh", "api_gateway", "distributed_systems"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        # DevOps specialist for microservices infrastructure
        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="DevOpsDev-Microservices",
                specialization="microservices_infrastructure",
                model_tier=ModelTier.SONNET,
                skills=["kubernetes", "service_discovery", "monitoring", "logging"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        return specialists

    def _get_data_pipeline_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for data pipeline projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="DataEngineer-Pipeline",
                specialization="data_engineering",
                model_tier=ModelTier.SONNET,
                skills=["data_pipelines", "etl", "apache_spark", "data_quality"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="DataEngineer-Storage",
                specialization="data_storage",
                model_tier=ModelTier.SONNET,
                skills=["data_warehousing", "nosql", "data_lakes", "optimization"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="DataDev-Analytics",
                specialization="analytics_platform",
                model_tier=ModelTier.SONNET,
                skills=["analytics", "visualization", "reporting", "dashboards"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        return specialists

    def _get_ml_project_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for ML projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="MLEngineer-Models",
                specialization="ml_engineering",
                model_tier=ModelTier.SONNET,
                skills=["machine_learning", "model_training", "feature_engineering"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="MLEngineer-Infrastructure",
                specialization="ml_infrastructure",
                model_tier=ModelTier.SONNET,
                skills=["mlops", "model_deployment", "model_monitoring"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="MLDev-Platform",
                specialization="ml_platform",
                model_tier=ModelTier.SONNET,
                skills=["ml_platforms", "experiment_tracking", "model_serving"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        return specialists

    def _get_devops_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for DevOps infrastructure projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="DevOpsDev-Infrastructure",
                specialization="infrastructure_automation",
                model_tier=ModelTier.SONNET,
                skills=[
                    "infrastructure_as_code",
                    "terraform",
                    "ansible",
                    "cloud_platforms",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="DevOpsDev-CICD",
                specialization="cicd_automation",
                model_tier=ModelTier.SONNET,
                skills=["ci_cd_pipelines", "automation", "testing_infrastructure"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="DevOpsDev-Monitoring",
                specialization="monitoring_observability",
                model_tier=ModelTier.SONNET,
                skills=[
                    "monitoring",
                    "logging",
                    "alerting",
                    "performance_optimization",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        return specialists

    def _get_frontend_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for frontend-only projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.FRONTEND_DEV,
                name="FrontendDev-Core",
                specialization="core_frontend",
                model_tier=ModelTier.SONNET,
                skills=[
                    "react",
                    "typescript",
                    "state_management",
                    "component_libraries",
                ],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        if requirements.team_size in [
            TeamSize.MEDIUM,
            TeamSize.LARGE,
            TeamSize.ENTERPRISE,
        ]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.FRONTEND_DEV,
                    name="FrontendDev-UX",
                    specialization="user_experience",
                    model_tier=ModelTier.SONNET,
                    skills=[
                        "ux_design",
                        "accessibility",
                        "responsive_design",
                        "animations",
                    ],
                    capacity_percentage=100.0,
                    cost_weight=1.0,
                )
            )

        return specialists

    def _get_backend_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for backend-only projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.BACKEND_DEV,
                name="BackendDev-Core",
                specialization="core_backend",
                model_tier=ModelTier.SONNET,
                skills=["api_development", "database_design", "business_logic"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        if requirements.team_size in [
            TeamSize.MEDIUM,
            TeamSize.LARGE,
            TeamSize.ENTERPRISE,
        ]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.BACKEND_DEV,
                    name="BackendDev-Integration",
                    specialization="system_integration",
                    model_tier=ModelTier.SONNET,
                    skills=["third_party_apis", "message_queues", "caching"],
                    capacity_percentage=100.0,
                    cost_weight=1.0,
                )
            )

        return specialists

    def _get_fullstack_specialists(
        self, requirements: TeamCompositionRequirements
    ) -> list[AgentSpecification]:
        """Get specialists for full-stack projects."""

        specialists = []

        specialists.append(
            AgentSpecification(
                role=AgentRole.FULLSTACK_DEV,
                name="FullstackDev-Primary",
                specialization="full_stack_development",
                model_tier=ModelTier.SONNET,
                skills=["full_stack", "end_to_end_features", "deployment"],
                capacity_percentage=100.0,
                cost_weight=1.0,
            )
        )

        if requirements.team_size in [
            TeamSize.MEDIUM,
            TeamSize.LARGE,
            TeamSize.ENTERPRISE,
        ]:
            specialists.append(
                AgentSpecification(
                    role=AgentRole.FULLSTACK_DEV,
                    name="FullstackDev-Secondary",
                    specialization="feature_development",
                    model_tier=ModelTier.SONNET,
                    skills=["feature_implementation", "testing", "optimization"],
                    capacity_percentage=100.0,
                    cost_weight=1.0,
                )
            )

        return specialists

    def _optimize_team_composition(
        self,
        agents: list[AgentSpecification],
        requirements: TeamCompositionRequirements,
    ) -> list[AgentSpecification]:
        """Optimize team composition based on constraints."""

        # Apply budget constraints
        if requirements.budget_constraints:
            agents = self._apply_budget_constraints(
                agents, requirements.budget_constraints
            )

        # Apply team size constraints
        agents = self._apply_team_size_constraints(agents, requirements.team_size)

        # Optimize for specific skills
        if requirements.specific_skills:
            agents = self._optimize_for_skills(agents, requirements.specific_skills)

        return agents

    def _apply_budget_constraints(
        self, agents: list[AgentSpecification], budget: float
    ) -> list[AgentSpecification]:
        """Apply budget constraints to team composition."""

        # Calculate current cost
        current_cost = sum(
            self.tier_costs[agent.model_tier] * agent.cost_weight for agent in agents
        )

        if current_cost <= budget:
            return agents

        # Reduce team if over budget
        # Priority: Keep coordination and architecture, reduce implementation
        essential_roles = {
            AgentRole.PRODUCT_OWNER,
            AgentRole.SCRUM_MASTER,
            AgentRole.TECH_LEAD,
        }

        essential_agents = [a for a in agents if a.role in essential_roles]
        other_agents = [a for a in agents if a.role not in essential_roles]

        # Sort other agents by cost efficiency (skills/cost ratio)
        other_agents.sort(
            key=lambda a: len(a.skills or []) / self.tier_costs[a.model_tier],
            reverse=True,
        )

        # Add agents while staying under budget
        optimized_agents = essential_agents.copy()
        remaining_budget = budget - sum(
            self.tier_costs[a.model_tier] for a in essential_agents
        )

        for agent in other_agents:
            agent_cost = self.tier_costs[agent.model_tier] * agent.cost_weight
            if agent_cost <= remaining_budget:
                optimized_agents.append(agent)
                remaining_budget -= agent_cost

        return optimized_agents

    def _apply_team_size_constraints(
        self, agents: list[AgentSpecification], team_size: TeamSize
    ) -> list[AgentSpecification]:
        """Apply team size constraints."""

        size_limits = {
            TeamSize.SMALL: 5,
            TeamSize.MEDIUM: 8,
            TeamSize.LARGE: 12,
            TeamSize.ENTERPRISE: 20,
        }

        max_agents = size_limits[team_size]

        if len(agents) <= max_agents:
            return agents

        # Prioritize agents by role importance and specialization
        role_priorities = {
            AgentRole.PRODUCT_OWNER: 10,
            AgentRole.SCRUM_MASTER: 9,
            AgentRole.TECH_LEAD: 8,
            AgentRole.QA_ENGINEER: 7,
            AgentRole.FULLSTACK_DEV: 6,
            AgentRole.BACKEND_DEV: 5,
            AgentRole.FRONTEND_DEV: 4,
        }

        agents_with_priority = [
            (
                agent,
                role_priorities.get(agent.role, 1) + (1 if agent.specialization else 0),
            )
            for agent in agents
        ]

        # Sort by priority and take top agents
        agents_with_priority.sort(key=lambda x: x[1], reverse=True)
        return [agent for agent, _ in agents_with_priority[:max_agents]]

    def _optimize_for_skills(
        self, agents: list[AgentSpecification], required_skills: list[str]
    ) -> list[AgentSpecification]:
        """Optimize team composition for specific skills."""

        # Check skill coverage
        covered_skills = set()
        for agent in agents:
            if agent.skills:
                covered_skills.update(agent.skills)

        missing_skills = set(required_skills) - covered_skills

        # If all skills are covered, return as-is
        if not missing_skills:
            return agents

        # Try to add agents or modify existing agents to cover missing skills
        # For simplification, we'll add missing skills to appropriate agents
        for skill in missing_skills:
            for agent in agents:
                if self._skill_matches_role(skill, agent.role):
                    if not agent.skills:
                        agent.skills = []
                    agent.skills.append(skill)
                    break

        return agents

    def _skill_matches_role(self, skill: str, role: AgentRole) -> bool:
        """Check if a skill matches an agent role."""

        frontend_skills = {
            "react",
            "typescript",
            "css",
            "html",
            "javascript",
            "responsive_design",
            "accessibility",
        }
        backend_skills = {
            "python",
            "fastapi",
            "postgresql",
            "redis",
            "docker",
            "api_development",
        }
        fullstack_skills = {"deployment", "devops", "ci_cd", "monitoring", "end_to_end"}
        qa_skills = {"testing", "automation", "quality_assurance", "test_planning"}

        return bool(
            role == AgentRole.FRONTEND_DEV
            and skill.lower() in frontend_skills
            or role == AgentRole.BACKEND_DEV
            and skill.lower() in backend_skills
            or role == AgentRole.FULLSTACK_DEV
            and skill.lower() in fullstack_skills
            or role == AgentRole.QA_ENGINEER
            and skill.lower() in qa_skills
        )

    def _finalize_composition(
        self,
        agents: list[AgentSpecification],
        requirements: TeamCompositionRequirements,
    ) -> TeamComposition:
        """Finalize the team composition with metrics and analysis."""

        # Calculate estimated cost
        estimated_cost = sum(
            self.tier_costs[agent.model_tier] * agent.cost_weight for agent in agents
        )

        # Calculate estimated velocity (simplified)
        dev_agents = [
            a
            for a in agents
            if a.role
            in {AgentRole.FRONTEND_DEV, AgentRole.BACKEND_DEV, AgentRole.FULLSTACK_DEV}
        ]
        estimated_velocity = (
            len(dev_agents) * 8.0
        )  # 8 story points per developer per sprint

        # Adjust for complexity
        complexity_multipliers = {
            ProjectComplexity.SIMPLE: 1.2,
            ProjectComplexity.MODERATE: 1.0,
            ProjectComplexity.COMPLEX: 0.8,
            ProjectComplexity.ENTERPRISE: 0.6,
        }
        estimated_velocity *= complexity_multipliers[requirements.complexity]

        # Identify strengths and limitations
        strengths, limitations = self._analyze_team_strengths_limitations(
            agents, requirements
        )

        # Generate success metrics
        success_metrics = self._generate_success_metrics(requirements)

        composition_id = f"comp_{requirements.project_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return TeamComposition(
            composition_id=composition_id,
            name=f"{requirements.project_type.value.replace('_', ' ').title()} Team",
            description=f"Custom team composition for {requirements.project_type.value} project with {requirements.complexity.value} complexity",
            project_type=requirements.project_type,
            agents=agents,
            estimated_cost_per_sprint=estimated_cost,
            estimated_velocity=estimated_velocity,
            strengths=strengths,
            limitations=limitations,
            success_metrics=success_metrics,
            created_at=datetime.now(),
        )

    def _analyze_team_strengths_limitations(
        self,
        agents: list[AgentSpecification],
        requirements: TeamCompositionRequirements,
    ) -> tuple[list[str], list[str]]:
        """Analyze team strengths and limitations."""

        strengths = []
        limitations = []

        # Analyze role coverage
        roles_present = {agent.role for agent in agents}

        if AgentRole.TECH_LEAD in roles_present:
            strengths.append("Strong technical leadership and architecture guidance")

        if AgentRole.QA_ENGINEER in roles_present:
            strengths.append("Dedicated quality assurance and testing")
        else:
            limitations.append("No dedicated QA engineer - testing may be limited")

        # Analyze specializations
        specializations = {
            agent.specialization for agent in agents if agent.specialization
        }

        if "performance_optimization" in specializations:
            strengths.append("Performance optimization expertise")

        if "security" in str(specializations):
            strengths.append("Security-focused development")

        # Analyze team balance
        dev_agents = [
            a
            for a in agents
            if a.role
            in {AgentRole.FRONTEND_DEV, AgentRole.BACKEND_DEV, AgentRole.FULLSTACK_DEV}
        ]

        if len(dev_agents) >= 3:
            strengths.append("Good parallel development capacity")
        elif len(dev_agents) < 2:
            limitations.append("Limited parallel development capacity")

        # Check for missing common needs
        if requirements.project_type in {
            ProjectType.WEB_APPLICATION,
            ProjectType.MOBILE_APP,
        }:
            if not any(agent.role == AgentRole.FRONTEND_DEV for agent in agents):
                limitations.append("No dedicated frontend expertise")

        if not any("devops" in (agent.skills or []) for agent in agents):
            limitations.append("Limited DevOps and deployment expertise")

        return strengths, limitations

    def _generate_success_metrics(
        self, requirements: TeamCompositionRequirements
    ) -> list[str]:
        """Generate success metrics for the team composition."""

        base_metrics = [
            "Sprint velocity consistency >90%",
            "Story completion rate >95%",
            "Team satisfaction score >8.0/10",
        ]

        if requirements.quality_requirements:
            base_metrics.extend(
                [
                    "Test coverage >90%",
                    "Bug escape rate <5%",
                    "Code review score >8.5/10",
                ]
            )

        if requirements.performance_requirements:
            base_metrics.append("Performance targets met >95% of the time")

        if requirements.budget_constraints:
            base_metrics.append(
                f"Stay within budget of ${requirements.budget_constraints:.2f} per sprint"
            )

        project_specific_metrics = {
            ProjectType.WEB_APPLICATION: [
                "Page load time <3 seconds",
                "Accessibility compliance 100%",
            ],
            ProjectType.MOBILE_APP: ["App store rating >4.5", "Crash rate <1%"],
            ProjectType.API_SERVICE: ["API response time <500ms", "99.9% uptime"],
            ProjectType.MICROSERVICES: [
                "Service independence maintained",
                "Circuit breaker effectiveness >95%",
            ],
            ProjectType.DATA_PIPELINE: [
                "Data quality >99.5%",
                "Pipeline reliability >99%",
            ],
            ProjectType.ML_PROJECT: [
                "Model accuracy meets targets",
                "Model deployment success >98%",
            ],
        }

        if requirements.project_type in project_specific_metrics:
            base_metrics.extend(project_specific_metrics[requirements.project_type])

        return base_metrics


class TeamCompositionManager:
    """Manages multiple team compositions and provides recommendations."""

    def __init__(self):
        self.builder = TeamCompositionBuilder()
        self.logger = get_logger("team_composition_manager")
        self.compositions_history: list[TeamComposition] = []

    async def recommend_team_composition(
        self, requirements: TeamCompositionRequirements
    ) -> dict[str, Any]:
        """Recommend optimal team composition with alternatives."""

        self.logger.info(
            "generating_team_recommendations",
            project_type=requirements.project_type.value,
        )

        # Generate primary recommendation
        primary_composition = await self.builder.build_team_composition(requirements)

        # Generate alternatives
        alternatives = await self._generate_alternatives(requirements)

        # Compare compositions
        comparison = self._compare_compositions([primary_composition] + alternatives)

        recommendation = {
            "primary_recommendation": self._composition_to_dict(primary_composition),
            "alternatives": [self._composition_to_dict(comp) for comp in alternatives],
            "comparison": comparison,
            "selection_guidance": self._generate_selection_guidance(
                primary_composition, alternatives, requirements
            ),
            "generated_at": datetime.now().isoformat(),
        }

        # Store composition
        self.compositions_history.append(primary_composition)

        self.logger.info(
            "team_recommendations_generated",
            primary_cost=primary_composition.estimated_cost_per_sprint,
            alternatives_count=len(alternatives),
        )

        return recommendation

    async def _generate_alternatives(
        self, requirements: TeamCompositionRequirements
    ) -> list[TeamComposition]:
        """Generate alternative team compositions."""

        alternatives = []

        # Budget-optimized alternative (if budget specified)
        if requirements.budget_constraints:
            budget_optimized_req = TeamCompositionRequirements(
                project_type=requirements.project_type,
                team_size=TeamSize.SMALL,  # Smaller team for budget
                complexity=requirements.complexity,
                budget_constraints=requirements.budget_constraints
                * 0.8,  # 20% less budget
                timeline_weeks=requirements.timeline_weeks,
                specific_skills=requirements.specific_skills,
            )
            budget_comp = await self.builder.build_team_composition(
                budget_optimized_req
            )
            alternatives.append(budget_comp)

        # Performance-optimized alternative
        perf_optimized_req = TeamCompositionRequirements(
            project_type=requirements.project_type,
            team_size=TeamSize.LARGE,  # Larger team for performance
            complexity=requirements.complexity,
            budget_constraints=None,  # No budget constraint
            timeline_weeks=requirements.timeline_weeks,
            specific_skills=(requirements.specific_skills or [])
            + ["performance_optimization"],
        )
        perf_comp = await self.builder.build_team_composition(perf_optimized_req)
        alternatives.append(perf_comp)

        return alternatives

    def _compare_compositions(
        self, compositions: list[TeamComposition]
    ) -> dict[str, Any]:
        """Compare multiple team compositions."""

        if not compositions:
            return {}

        comparison = {
            "cost_comparison": {
                "lowest_cost": min(
                    comp.estimated_cost_per_sprint for comp in compositions
                ),
                "highest_cost": max(
                    comp.estimated_cost_per_sprint for comp in compositions
                ),
                "average_cost": sum(
                    comp.estimated_cost_per_sprint for comp in compositions
                )
                / len(compositions),
            },
            "velocity_comparison": {
                "lowest_velocity": min(
                    comp.estimated_velocity for comp in compositions
                ),
                "highest_velocity": max(
                    comp.estimated_velocity for comp in compositions
                ),
                "average_velocity": sum(
                    comp.estimated_velocity for comp in compositions
                )
                / len(compositions),
            },
            "team_size_comparison": {
                "smallest_team": min(len(comp.agents) for comp in compositions),
                "largest_team": max(len(comp.agents) for comp in compositions),
                "average_team_size": sum(len(comp.agents) for comp in compositions)
                / len(compositions),
            },
            "value_analysis": [],
        }

        # Value analysis
        for i, comp in enumerate(compositions):
            cost_efficiency = comp.estimated_velocity / comp.estimated_cost_per_sprint
            value_score = (
                cost_efficiency * len(comp.strengths) / max(1, len(comp.limitations))
            )

            comparison["value_analysis"].append(
                {
                    "composition_index": i,
                    "name": comp.name,
                    "cost_efficiency": cost_efficiency,
                    "value_score": value_score,
                    "strengths_count": len(comp.strengths),
                    "limitations_count": len(comp.limitations),
                }
            )

        # Sort by value score
        comparison["value_analysis"].sort(key=lambda x: x["value_score"], reverse=True)

        return comparison

    def _generate_selection_guidance(
        self,
        primary: TeamComposition,
        alternatives: list[TeamComposition],
        requirements: TeamCompositionRequirements,
    ) -> dict[str, str]:
        """Generate guidance for selecting between compositions."""

        guidance = {
            "primary_recommendation_reason": f"Balanced team optimized for {requirements.project_type.value} with {requirements.complexity.value} complexity",
            "when_to_choose_primary": f"Choose when you need a well-balanced team with estimated velocity of {primary.estimated_velocity:.1f} story points per sprint",
            "alternative_recommendations": {},
        }

        for i, alt in enumerate(alternatives):
            if alt.estimated_cost_per_sprint < primary.estimated_cost_per_sprint:
                guidance["alternative_recommendations"][
                    f"alternative_{i+1}"
                ] = f"Choose for budget optimization - {((primary.estimated_cost_per_sprint - alt.estimated_cost_per_sprint) / primary.estimated_cost_per_sprint * 100):.1f}% cost reduction"
            elif alt.estimated_velocity > primary.estimated_velocity:
                guidance["alternative_recommendations"][
                    f"alternative_{i+1}"
                ] = f"Choose for higher velocity - {((alt.estimated_velocity - primary.estimated_velocity) / primary.estimated_velocity * 100):.1f}% velocity increase"

        # Add constraint-based guidance
        if requirements.budget_constraints:
            within_budget = [
                comp
                for comp in [primary] + alternatives
                if comp.estimated_cost_per_sprint <= requirements.budget_constraints
            ]
            if within_budget:
                best_in_budget = max(within_budget, key=lambda c: c.estimated_velocity)
                guidance["budget_constrained_choice"] = (
                    f"Best option within budget: {best_in_budget.name}"
                )

        if requirements.timeline_weeks and requirements.timeline_weeks < 4:
            guidance["timeline_constrained_choice"] = (
                "For short timelines, choose higher velocity options even if more expensive"
            )

        return guidance

    def _composition_to_dict(self, composition: TeamComposition) -> dict[str, Any]:
        """Convert team composition to dictionary format."""

        return {
            "composition_id": composition.composition_id,
            "name": composition.name,
            "description": composition.description,
            "project_type": composition.project_type.value,
            "agents": [
                {
                    "role": agent.role.value,
                    "name": agent.name,
                    "specialization": agent.specialization,
                    "model_tier": agent.model_tier.value,
                    "skills": agent.skills or [],
                    "capacity_percentage": agent.capacity_percentage,
                    "cost_weight": agent.cost_weight,
                }
                for agent in composition.agents
            ],
            "estimated_cost_per_sprint": composition.estimated_cost_per_sprint,
            "estimated_velocity": composition.estimated_velocity,
            "strengths": composition.strengths,
            "limitations": composition.limitations,
            "success_metrics": composition.success_metrics,
            "created_at": composition.created_at.isoformat(),
            "team_size": len(composition.agents),
            "cost_per_story_point": composition.estimated_cost_per_sprint
            / max(1, composition.estimated_velocity),
        }
