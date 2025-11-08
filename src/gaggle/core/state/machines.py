"""Agent state machines for context-aware coordination."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ...config.models import AgentRole
from ..communication.messages import AgentMessage, MessageType


class AgentState(Enum):
    """Common agent states across all roles."""

    IDLE = "idle"
    PLANNING = "planning"
    WORKING = "working"
    REVIEWING = "reviewing"
    BLOCKED = "blocked"
    COORDINATING = "coordinating"
    ERROR = "error"


@dataclass
class StateTransition:
    """Defines a state transition with conditions and actions."""

    from_state: AgentState
    to_state: AgentState
    trigger: str  # What triggers this transition
    condition: Callable[[Any], bool] | None = None  # Additional condition check
    action: Callable[[Any], Any] | None = None  # Action to perform during transition

    def can_transition(self, context: Any = None) -> bool:
        """Check if transition can be performed."""
        if self.condition is None:
            return True
        return self.condition(context)

    def execute_action(self, context: Any = None) -> Any:
        """Execute transition action."""
        if self.action:
            return self.action(context)
        return None


@dataclass
class StateMachineConfig:
    """Configuration for agent state machine."""

    initial_state: AgentState = AgentState.IDLE
    valid_states: set[AgentState] = field(default_factory=lambda: set(AgentState))
    transitions: list[StateTransition] = field(default_factory=list)
    state_timeouts: dict[AgentState, float] = field(
        default_factory=dict
    )  # Timeout in seconds

    def add_transition(self, transition: StateTransition) -> None:
        """Add a state transition."""
        self.transitions.append(transition)

    def get_transitions_from_state(self, state: AgentState) -> list[StateTransition]:
        """Get all possible transitions from a state."""
        return [t for t in self.transitions if t.from_state == state]


class AgentStateMachine(ABC):
    """Base class for agent state machines."""

    def __init__(
        self,
        agent_role: AgentRole,
        agent_id: str,
        config: StateMachineConfig | None = None,
    ):
        self.agent_role = agent_role
        self.agent_id = agent_id
        self.config = config or self._get_default_config()

        self.current_state = self.config.initial_state
        self.previous_state: AgentState | None = None
        self.state_entered_at = datetime.now()
        self.state_history: list[tuple[AgentState, datetime, datetime]] = []

        # Context and coordination
        self.context_data: dict[str, Any] = {}
        self.available_actions: set[str] = set()
        self.blocked_by: list[str] = []
        self.current_message: AgentMessage | None = None

        self.logger = logging.getLogger(f"state.{agent_role.value}.{agent_id}")

        # Initialize available actions for current state
        self._update_available_actions()

    @abstractmethod
    def _get_default_config(self) -> StateMachineConfig:
        """Get default configuration for this agent type."""
        pass

    @abstractmethod
    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get available capabilities/actions for a state."""
        pass

    @abstractmethod
    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if agent can handle a message in current state."""
        pass

    def transition_to(
        self, new_state: AgentState, trigger: str = "manual", context: Any = None
    ) -> bool:
        """Attempt to transition to a new state."""

        if new_state not in self.config.valid_states:
            self.logger.warning(
                f"Invalid state transition attempted: {self.current_state} -> {new_state}"
            )
            return False

        # Find applicable transition
        applicable_transitions = [
            t
            for t in self.config.get_transitions_from_state(self.current_state)
            if t.to_state == new_state and t.trigger == trigger
        ]

        if not applicable_transitions:
            self.logger.warning(
                f"No valid transition found: {self.current_state} -> {new_state} (trigger: {trigger})"
            )
            return False

        transition = applicable_transitions[0]  # Use first matching transition

        # Check transition condition
        if not transition.can_transition(context):
            self.logger.warning(
                f"Transition condition failed: {self.current_state} -> {new_state}"
            )
            return False

        # Record state history
        if self.current_state != new_state:
            self.state_history.append(
                (self.current_state, self.state_entered_at, datetime.now())
            )

        # Execute transition
        old_state = self.current_state
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_entered_at = datetime.now()

        # Execute transition action
        try:
            transition.execute_action(context)
        except Exception as e:
            self.logger.error(f"Transition action failed: {e}")

        # Update available actions
        self._update_available_actions()

        # Clear blockers if transitioning out of blocked state
        if old_state == AgentState.BLOCKED and new_state != AgentState.BLOCKED:
            self.blocked_by.clear()

        self.logger.info(
            f"State transition: {old_state.value} -> {new_state.value} (trigger: {trigger})"
        )
        return True

    def _update_available_actions(self) -> None:
        """Update available actions based on current state."""
        self.available_actions = self.get_capabilities_for_state(self.current_state)

    def is_available_for_work(self) -> bool:
        """Check if agent is available to take on new work."""
        return self.current_state in [AgentState.IDLE, AgentState.COORDINATING]

    def is_blocked(self) -> bool:
        """Check if agent is currently blocked."""
        return self.current_state == AgentState.BLOCKED

    def add_blocker(self, blocker: str) -> None:
        """Add a blocker and transition to blocked state if needed."""
        if blocker not in self.blocked_by:
            self.blocked_by.append(blocker)

        if self.current_state != AgentState.BLOCKED:
            self.transition_to(AgentState.BLOCKED, "blocked", {"blocker": blocker})

    def remove_blocker(self, blocker: str) -> None:
        """Remove a blocker and potentially unblock agent."""
        if blocker in self.blocked_by:
            self.blocked_by.remove(blocker)

        # If no more blockers, transition out of blocked state
        if not self.blocked_by and self.current_state == AgentState.BLOCKED:
            target_state = self.previous_state or AgentState.IDLE
            self.transition_to(target_state, "unblocked")

    def set_context(self, key: str, value: Any) -> None:
        """Set context data."""
        self.context_data[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context data."""
        return self.context_data.get(key, default)

    def get_state_info(self) -> dict[str, Any]:
        """Get current state information."""
        return {
            "agent_role": self.agent_role.value,
            "agent_id": self.agent_id,
            "current_state": self.current_state.value,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "state_entered_at": self.state_entered_at.isoformat(),
            "time_in_state": (datetime.now() - self.state_entered_at).total_seconds(),
            "available_actions": list(self.available_actions),
            "blocked_by": self.blocked_by,
            "context_data": self.context_data,
        }


class ProductOwnerStateMachine(AgentStateMachine):
    """State machine for Product Owner agent."""

    def _get_default_config(self) -> StateMachineConfig:
        """Get Product Owner state machine configuration."""
        config = StateMachineConfig(
            initial_state=AgentState.IDLE,
            valid_states={
                AgentState.IDLE,
                AgentState.PLANNING,
                AgentState.REVIEWING,
                AgentState.COORDINATING,
                AgentState.BLOCKED,
            },
        )

        # Define transitions
        transitions = [
            StateTransition(
                AgentState.IDLE, AgentState.PLANNING, "sprint_planning_started"
            ),
            StateTransition(
                AgentState.IDLE,
                AgentState.COORDINATING,
                "requirement_clarification_requested",
            ),
            StateTransition(
                AgentState.PLANNING, AgentState.COORDINATING, "stakeholder_input_needed"
            ),
            StateTransition(AgentState.PLANNING, AgentState.IDLE, "planning_completed"),
            StateTransition(
                AgentState.COORDINATING, AgentState.PLANNING, "requirements_clarified"
            ),
            StateTransition(
                AgentState.COORDINATING, AgentState.REVIEWING, "sprint_review_started"
            ),
            StateTransition(AgentState.REVIEWING, AgentState.IDLE, "review_completed"),
            # Blocked state transitions
            StateTransition(AgentState.IDLE, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.PLANNING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.COORDINATING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.REVIEWING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.BLOCKED, AgentState.IDLE, "unblocked"),
        ]

        for transition in transitions:
            config.add_transition(transition)

        return config

    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get Product Owner capabilities for each state."""
        capabilities = {
            AgentState.IDLE: {
                "clarify_requirements",
                "prioritize_backlog",
                "accept_new_requests",
            },
            AgentState.PLANNING: {
                "create_user_stories",
                "define_acceptance_criteria",
                "prioritize_stories",
                "estimate_business_value",
            },
            AgentState.COORDINATING: {
                "answer_requirements_questions",
                "provide_clarifications",
                "negotiate_scope",
            },
            AgentState.REVIEWING: {
                "review_deliverables",
                "accept_or_reject_work",
                "provide_feedback",
            },
            AgentState.BLOCKED: set(),
        }

        return capabilities.get(state, set())

    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if PO can handle message in current state."""
        message_handlers = {
            MessageType.REQUIREMENT_CLARIFICATION: [
                AgentState.IDLE,
                AgentState.COORDINATING,
                AgentState.PLANNING,
            ],
            MessageType.SPRINT_PLANNING: [AgentState.IDLE, AgentState.PLANNING],
            MessageType.STANDUP_UPDATE: [AgentState.IDLE, AgentState.COORDINATING],
        }

        return self.current_state in message_handlers.get(message.message_type, [])


class ScrumMasterStateMachine(AgentStateMachine):
    """State machine for Scrum Master agent."""

    def _get_default_config(self) -> StateMachineConfig:
        """Get Scrum Master state machine configuration."""
        config = StateMachineConfig(
            initial_state=AgentState.IDLE,
            valid_states={
                AgentState.IDLE,
                AgentState.PLANNING,
                AgentState.COORDINATING,
                AgentState.REVIEWING,
                AgentState.BLOCKED,
            },
        )

        transitions = [
            StateTransition(
                AgentState.IDLE, AgentState.PLANNING, "sprint_planning_initiated"
            ),
            StateTransition(
                AgentState.IDLE, AgentState.COORDINATING, "daily_standup_time"
            ),
            StateTransition(AgentState.PLANNING, AgentState.IDLE, "sprint_planned"),
            StateTransition(
                AgentState.COORDINATING, AgentState.IDLE, "coordination_completed"
            ),
            StateTransition(
                AgentState.COORDINATING, AgentState.REVIEWING, "retrospective_time"
            ),
            StateTransition(
                AgentState.REVIEWING, AgentState.IDLE, "retrospective_completed"
            ),
            # Blocked transitions
            StateTransition(AgentState.IDLE, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.PLANNING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.COORDINATING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.REVIEWING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.BLOCKED, AgentState.IDLE, "unblocked"),
        ]

        for transition in transitions:
            config.add_transition(transition)

        return config

    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get Scrum Master capabilities for each state."""
        capabilities = {
            AgentState.IDLE: {
                "facilitate_ceremonies",
                "remove_blockers",
                "track_metrics",
            },
            AgentState.PLANNING: {
                "facilitate_sprint_planning",
                "coordinate_capacity_planning",
                "finalize_sprint_commitment",
            },
            AgentState.COORDINATING: {
                "run_daily_standups",
                "identify_blockers",
                "coordinate_team_communication",
                "track_progress",
            },
            AgentState.REVIEWING: {
                "facilitate_retrospective",
                "collect_feedback",
                "identify_improvements",
            },
            AgentState.BLOCKED: set(),
        }

        return capabilities.get(state, set())

    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if SM can handle message in current state."""
        message_handlers = {
            MessageType.SPRINT_PLANNING: [AgentState.IDLE, AgentState.PLANNING],
            MessageType.STANDUP_UPDATE: [AgentState.IDLE, AgentState.COORDINATING],
            MessageType.COORDINATION_REQUEST: [
                AgentState.IDLE,
                AgentState.COORDINATING,
                AgentState.PLANNING,
            ],
        }

        return self.current_state in message_handlers.get(message.message_type, [])


class TechLeadStateMachine(AgentStateMachine):
    """State machine for Tech Lead agent."""

    def _get_default_config(self) -> StateMachineConfig:
        """Get Tech Lead state machine configuration."""
        config = StateMachineConfig(
            initial_state=AgentState.IDLE,
            valid_states={
                AgentState.IDLE,
                AgentState.PLANNING,
                AgentState.WORKING,
                AgentState.REVIEWING,
                AgentState.COORDINATING,
                AgentState.BLOCKED,
            },
        )

        transitions = [
            StateTransition(
                AgentState.IDLE, AgentState.PLANNING, "architecture_planning_needed"
            ),
            StateTransition(
                AgentState.IDLE, AgentState.REVIEWING, "code_review_requested"
            ),
            StateTransition(
                AgentState.IDLE, AgentState.WORKING, "architecture_task_assigned"
            ),
            StateTransition(
                AgentState.PLANNING, AgentState.WORKING, "architecture_decided"
            ),
            StateTransition(AgentState.PLANNING, AgentState.IDLE, "planning_completed"),
            StateTransition(
                AgentState.WORKING, AgentState.REVIEWING, "architecture_completed"
            ),
            StateTransition(AgentState.WORKING, AgentState.IDLE, "task_completed"),
            StateTransition(AgentState.REVIEWING, AgentState.IDLE, "review_completed"),
            StateTransition(
                AgentState.REVIEWING, AgentState.COORDINATING, "review_feedback_needed"
            ),
            StateTransition(
                AgentState.COORDINATING, AgentState.IDLE, "coordination_completed"
            ),
            # Blocked transitions
            StateTransition(AgentState.IDLE, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.PLANNING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.WORKING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.REVIEWING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.COORDINATING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.BLOCKED, AgentState.IDLE, "unblocked"),
        ]

        for transition in transitions:
            config.add_transition(transition)

        return config

    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get Tech Lead capabilities for each state."""
        capabilities = {
            AgentState.IDLE: {
                "accept_review_requests",
                "provide_architecture_guidance",
                "answer_technical_questions",
            },
            AgentState.PLANNING: {
                "make_architecture_decisions",
                "break_down_technical_stories",
                "design_system_components",
                "plan_technical_approach",
            },
            AgentState.WORKING: {
                "create_architectural_components",
                "generate_code_templates",
                "implement_core_infrastructure",
            },
            AgentState.REVIEWING: {
                "review_code_quality",
                "check_architectural_compliance",
                "provide_improvement_suggestions",
            },
            AgentState.COORDINATING: {
                "guide_implementation_approach",
                "resolve_technical_conflicts",
                "coordinate_with_developers",
            },
            AgentState.BLOCKED: set(),
        }

        return capabilities.get(state, set())

    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if Tech Lead can handle message in current state."""
        message_handlers = {
            MessageType.ARCHITECTURE_DECISION: [
                AgentState.IDLE,
                AgentState.PLANNING,
                AgentState.COORDINATING,
            ],
            MessageType.CODE_REVIEW: [AgentState.IDLE, AgentState.REVIEWING],
            MessageType.TASK_ASSIGNMENT: [AgentState.IDLE],
        }

        return self.current_state in message_handlers.get(message.message_type, [])


class DeveloperStateMachine(AgentStateMachine):
    """State machine for Developer agents (Frontend, Backend, Fullstack)."""

    def _get_default_config(self) -> StateMachineConfig:
        """Get Developer state machine configuration."""
        config = StateMachineConfig(
            initial_state=AgentState.IDLE,
            valid_states={
                AgentState.IDLE,
                AgentState.WORKING,
                AgentState.COORDINATING,
                AgentState.BLOCKED,
            },
        )

        transitions = [
            StateTransition(AgentState.IDLE, AgentState.WORKING, "task_assigned"),
            StateTransition(
                AgentState.IDLE, AgentState.COORDINATING, "clarification_needed"
            ),
            StateTransition(AgentState.WORKING, AgentState.COORDINATING, "help_needed"),
            StateTransition(AgentState.WORKING, AgentState.IDLE, "task_completed"),
            StateTransition(
                AgentState.COORDINATING, AgentState.WORKING, "clarification_received"
            ),
            StateTransition(
                AgentState.COORDINATING, AgentState.IDLE, "coordination_completed"
            ),
            # Blocked transitions
            StateTransition(AgentState.IDLE, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.WORKING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.COORDINATING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.BLOCKED, AgentState.IDLE, "unblocked"),
        ]

        for transition in transitions:
            config.add_transition(transition)

        return config

    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get Developer capabilities for each state."""
        capabilities = {
            AgentState.IDLE: {
                "accept_task_assignments",
                "provide_estimates",
                "participate_in_standups",
            },
            AgentState.WORKING: {
                "implement_features",
                "write_code",
                "run_tests",
                "commit_changes",
                "update_documentation",
            },
            AgentState.COORDINATING: {
                "ask_for_clarification",
                "report_blockers",
                "collaborate_with_team",
            },
            AgentState.BLOCKED: set(),
        }

        return capabilities.get(state, set())

    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if Developer can handle message in current state."""
        message_handlers = {
            MessageType.TASK_ASSIGNMENT: [AgentState.IDLE],
            MessageType.STANDUP_UPDATE: [
                AgentState.IDLE,
                AgentState.WORKING,
                AgentState.COORDINATING,
            ],
            MessageType.CODE_REVIEW: [AgentState.IDLE, AgentState.WORKING],
        }

        return self.current_state in message_handlers.get(message.message_type, [])


class QAEngineerStateMachine(AgentStateMachine):
    """State machine for QA Engineer agent."""

    def _get_default_config(self) -> StateMachineConfig:
        """Get QA Engineer state machine configuration."""
        config = StateMachineConfig(
            initial_state=AgentState.IDLE,
            valid_states={
                AgentState.IDLE,
                AgentState.PLANNING,
                AgentState.WORKING,
                AgentState.REVIEWING,
                AgentState.BLOCKED,
            },
        )

        transitions = [
            StateTransition(
                AgentState.IDLE, AgentState.PLANNING, "test_planning_needed"
            ),
            StateTransition(
                AgentState.IDLE, AgentState.WORKING, "testing_task_assigned"
            ),
            StateTransition(
                AgentState.IDLE, AgentState.REVIEWING, "code_review_requested"
            ),
            StateTransition(
                AgentState.PLANNING, AgentState.WORKING, "test_plan_completed"
            ),
            StateTransition(AgentState.PLANNING, AgentState.IDLE, "planning_deferred"),
            StateTransition(AgentState.WORKING, AgentState.IDLE, "testing_completed"),
            StateTransition(AgentState.WORKING, AgentState.REVIEWING, "defects_found"),
            StateTransition(AgentState.REVIEWING, AgentState.IDLE, "review_completed"),
            StateTransition(AgentState.REVIEWING, AgentState.WORKING, "retest_needed"),
            # Blocked transitions
            StateTransition(AgentState.IDLE, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.PLANNING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.WORKING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.REVIEWING, AgentState.BLOCKED, "blocked"),
            StateTransition(AgentState.BLOCKED, AgentState.IDLE, "unblocked"),
        ]

        for transition in transitions:
            config.add_transition(transition)

        return config

    def get_capabilities_for_state(self, state: AgentState) -> set[str]:
        """Get QA Engineer capabilities for each state."""
        capabilities = {
            AgentState.IDLE: {
                "accept_testing_assignments",
                "provide_quality_insights",
                "participate_in_ceremonies",
            },
            AgentState.PLANNING: {
                "create_test_plans",
                "design_test_cases",
                "identify_testing_scope",
            },
            AgentState.WORKING: {
                "execute_test_cases",
                "automated_testing",
                "manual_testing",
                "report_defects",
                "verify_fixes",
            },
            AgentState.REVIEWING: {
                "review_code_quality",
                "verify_test_coverage",
                "assess_quality_metrics",
            },
            AgentState.BLOCKED: set(),
        }

        return capabilities.get(state, set())

    def can_handle_message(self, message: AgentMessage) -> bool:
        """Check if QA Engineer can handle message in current state."""
        message_handlers = {
            MessageType.TASK_ASSIGNMENT: [AgentState.IDLE],
            MessageType.QUALITY_REPORT: [AgentState.IDLE, AgentState.REVIEWING],
            MessageType.CODE_REVIEW: [AgentState.IDLE, AgentState.REVIEWING],
        }

        return self.current_state in message_handlers.get(message.message_type, [])
