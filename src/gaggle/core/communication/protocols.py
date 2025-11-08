"""Communication protocols and validation for structured agent coordination."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from ...config.models import AgentRole
from .messages import AgentMessage, MessageType, ValidationResult


class ProtocolState(Enum):
    """States in communication protocols."""

    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    AWAITING_RESPONSE = "awaiting_response"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CommunicationProtocol(ABC):
    """Base class for structured communication protocols."""

    def __init__(self, protocol_id: str, initiator: AgentRole):
        self.protocol_id = protocol_id
        self.initiator = initiator
        self.state = ProtocolState.INITIATED
        self.messages: list[AgentMessage] = []
        self.participants: list[AgentRole] = [initiator]
        self.logger = logging.getLogger(f"protocol.{self.__class__.__name__}")

    @abstractmethod
    def get_expected_message_types(self) -> list[MessageType]:
        """Get the types of messages expected in this protocol."""
        pass

    @abstractmethod
    def validate_message_sequence(self, message: AgentMessage) -> ValidationResult:
        """Validate that a message fits the expected protocol sequence."""
        pass

    @abstractmethod
    def get_next_expected_actions(self) -> list[str]:
        """Get description of next expected actions in the protocol."""
        pass

    def add_participant(self, role: AgentRole) -> None:
        """Add a participant to the protocol."""
        if role not in self.participants:
            self.participants.append(role)

    def add_message(self, message: AgentMessage) -> ValidationResult:
        """Add a message to the protocol and validate it."""
        validation = self.validate_message_sequence(message)

        if validation.is_valid:
            self.messages.append(message)
            self._update_state_from_message(message)
            self.logger.info(
                f"Message added to protocol {self.protocol_id}: {message.id}"
            )
        else:
            self.logger.warning(
                f"Invalid message for protocol {self.protocol_id}: {validation.errors}"
            )

        return validation

    def _update_state_from_message(self, message: AgentMessage) -> None:
        """Update protocol state based on received message."""
        if self.state == ProtocolState.INITIATED:
            self.state = ProtocolState.IN_PROGRESS
        elif message.requires_response:
            self.state = ProtocolState.AWAITING_RESPONSE

    def is_complete(self) -> bool:
        """Check if protocol is complete."""
        return self.state == ProtocolState.COMPLETED

    def can_accept_message(self, message: AgentMessage) -> bool:
        """Check if protocol can accept a message."""
        return (
            self.state
            not in [
                ProtocolState.COMPLETED,
                ProtocolState.FAILED,
                ProtocolState.CANCELLED,
            ]
            and message.message_type in self.get_expected_message_types()
        )


class TaskAssignmentProtocol(CommunicationProtocol):
    """Protocol for task assignment workflow."""

    def get_expected_message_types(self) -> list[MessageType]:
        """Task assignment expects task assignments and confirmations."""
        return [MessageType.TASK_ASSIGNMENT, MessageType.COORDINATION_REQUEST]

    def validate_message_sequence(self, message: AgentMessage) -> ValidationResult:
        """Validate task assignment protocol sequence."""
        result = ValidationResult(is_valid=True)

        # First message should be task assignment
        if not self.messages and message.message_type != MessageType.TASK_ASSIGNMENT:
            result.add_error("Protocol must start with TASK_ASSIGNMENT message")

        # Check sender permissions
        if message.message_type == MessageType.TASK_ASSIGNMENT:
            if message.sender not in [AgentRole.TECH_LEAD, AgentRole.SCRUM_MASTER]:
                result.add_error("Only Tech Lead or Scrum Master can assign tasks")

        return result

    def get_next_expected_actions(self) -> list[str]:
        """Get next expected actions for task assignment."""
        if not self.messages:
            return ["Tech Lead or Scrum Master should send task assignment"]

        last_message = self.messages[-1]
        if last_message.message_type == MessageType.TASK_ASSIGNMENT:
            return ["Assigned agent should acknowledge task assignment"]

        return ["Protocol should be completed"]


class SprintPlanningProtocol(CommunicationProtocol):
    """Protocol for sprint planning workflow."""

    def get_expected_message_types(self) -> list[MessageType]:
        """Sprint planning expects planning messages and clarifications."""
        return [
            MessageType.SPRINT_PLANNING,
            MessageType.REQUIREMENT_CLARIFICATION,
            MessageType.TASK_ASSIGNMENT,
            MessageType.ARCHITECTURE_DECISION,
        ]

    def validate_message_sequence(self, message: AgentMessage) -> ValidationResult:
        """Validate sprint planning protocol sequence."""
        result = ValidationResult(is_valid=True)

        # Protocol should start with Product Owner clarifications
        if not self.messages and message.sender != AgentRole.PRODUCT_OWNER:
            result.add_warning("Sprint planning typically starts with Product Owner")

        # Validate planning authority
        if message.message_type == MessageType.SPRINT_PLANNING:
            if message.sender != AgentRole.SCRUM_MASTER:
                result.add_error("Only Scrum Master can finalize sprint planning")

        return result

    def get_next_expected_actions(self) -> list[str]:
        """Get next expected actions for sprint planning."""
        if not self.messages:
            return ["Product Owner should clarify requirements"]

        message_types = [msg.message_type for msg in self.messages]

        if MessageType.REQUIREMENT_CLARIFICATION not in message_types:
            return ["Product Owner should clarify requirements"]
        elif MessageType.ARCHITECTURE_DECISION not in message_types:
            return ["Tech Lead should make architecture decisions"]
        elif MessageType.SPRINT_PLANNING not in message_types:
            return ["Scrum Master should finalize sprint plan"]
        else:
            return ["Begin sprint execution"]


class CodeReviewProtocol(CommunicationProtocol):
    """Protocol for code review workflow."""

    def get_expected_message_types(self) -> list[MessageType]:
        """Code review expects review messages."""
        return [MessageType.CODE_REVIEW, MessageType.COORDINATION_REQUEST]

    def validate_message_sequence(self, message: AgentMessage) -> ValidationResult:
        """Validate code review protocol sequence."""
        result = ValidationResult(is_valid=True)

        # Check reviewer authority
        if message.message_type == MessageType.CODE_REVIEW:
            if message.sender not in [AgentRole.TECH_LEAD, AgentRole.QA_ENGINEER]:
                result.add_warning(
                    "Code reviews typically done by Tech Lead or QA Engineer"
                )

        return result

    def get_next_expected_actions(self) -> list[str]:
        """Get next expected actions for code review."""
        if not self.messages:
            return ["Submit code for review"]

        last_message = self.messages[-1]
        if last_message.message_type == MessageType.CODE_REVIEW:
            return [
                (
                    "Address review feedback"
                    if not getattr(last_message, "approved", True)
                    else "Merge approved code"
                )
            ]

        return ["Complete review process"]


@dataclass
class ProtocolValidator:
    """Validates communication protocols and message flows."""

    active_protocols: dict[str, CommunicationProtocol] = field(default_factory=dict)
    protocol_registry: dict[MessageType, type[CommunicationProtocol]] = field(
        default_factory=dict
    )
    logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("protocol.validator")
    )

    def __post_init__(self):
        """Initialize protocol registry."""
        self.protocol_registry = {
            MessageType.TASK_ASSIGNMENT: TaskAssignmentProtocol,
            MessageType.SPRINT_PLANNING: SprintPlanningProtocol,
            MessageType.CODE_REVIEW: CodeReviewProtocol,
        }

    def validate_message(self, message: AgentMessage) -> ValidationResult:
        """Validate a message against active protocols."""
        result = ValidationResult(is_valid=True)

        # First validate the message itself
        message_validation = message.validate()
        if not message_validation.is_valid:
            result.errors.extend(message_validation.errors)
            result.warnings.extend(message_validation.warnings)
            result.is_valid = False

        # Find or create appropriate protocol
        protocol = self._find_or_create_protocol(message)

        if protocol:
            # Validate against protocol
            protocol_validation = protocol.add_message(message)
            if not protocol_validation.is_valid:
                result.errors.extend(protocol_validation.errors)
                result.warnings.extend(protocol_validation.warnings)
                result.is_valid = False
        else:
            result.add_warning(
                f"No protocol handler for message type {message.message_type.value}"
            )

        return result

    def _find_or_create_protocol(
        self, message: AgentMessage
    ) -> CommunicationProtocol | None:
        """Find existing protocol or create new one for message."""

        # Look for existing protocol by correlation ID
        if message.correlation_id:
            for protocol in self.active_protocols.values():
                if any(
                    msg.correlation_id == message.correlation_id
                    for msg in protocol.messages
                ):
                    return protocol

        # Look for existing protocol that can accept this message type
        for protocol in self.active_protocols.values():
            if protocol.can_accept_message(message):
                return protocol

        # Create new protocol if we have a handler
        protocol_class = self.protocol_registry.get(message.message_type)
        if protocol_class:
            protocol_id = f"{message.message_type.value}_{message.id[:8]}"
            protocol = protocol_class(protocol_id, message.sender)
            self.active_protocols[protocol_id] = protocol
            self.logger.info(f"Created new protocol {protocol_id}")
            return protocol

        return None

    def get_active_protocols(self) -> dict[str, CommunicationProtocol]:
        """Get all active protocols."""
        return self.active_protocols.copy()

    def cleanup_completed_protocols(self) -> int:
        """Remove completed protocols and return count removed."""
        completed_protocols = [
            protocol_id
            for protocol_id, protocol in self.active_protocols.items()
            if protocol.is_complete()
        ]

        for protocol_id in completed_protocols:
            del self.active_protocols[protocol_id]
            self.logger.info(f"Cleaned up completed protocol {protocol_id}")

        return len(completed_protocols)

    def get_protocol_status(self) -> dict[str, dict]:
        """Get status of all protocols."""
        status = {}
        for protocol_id, protocol in self.active_protocols.items():
            status[protocol_id] = {
                "state": protocol.state.value,
                "participants": [role.value for role in protocol.participants],
                "message_count": len(protocol.messages),
                "next_actions": protocol.get_next_expected_actions(),
            }
        return status
