"""Message bus and routing for agent communication."""

import asyncio
import contextlib
import logging
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ...config.models import AgentRole
from .messages import AgentMessage, MessagePriority, MessageType, ValidationResult
from .protocols import ProtocolValidator


@dataclass
class MessageHandler:
    """Handler for processing messages."""

    handler_id: str
    agent_role: AgentRole
    message_types: set[MessageType]
    callback: Callable[[AgentMessage], Any]
    is_async: bool = True

    def can_handle(self, message: AgentMessage) -> bool:
        """Check if handler can process this message."""
        return message.message_type in self.message_types and (
            message.recipient is None or message.recipient == self.agent_role
        )


@dataclass
class MessageRoute:
    """Routing information for messages."""

    source: AgentRole
    destination: AgentRole
    message_type: MessageType
    priority: MessagePriority = MessagePriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)


class MessageRouter:
    """Routes messages between agents based on patterns and rules."""

    def __init__(self):
        self.routes: dict[str, MessageRoute] = {}
        self.routing_rules: dict[MessageType, list[AgentRole]] = {}
        self.logger = logging.getLogger("message.router")

        # Initialize default routing rules
        self._setup_default_routes()

    def _setup_default_routes(self) -> None:
        """Setup default message routing rules."""
        self.routing_rules = {
            MessageType.TASK_ASSIGNMENT: [
                AgentRole.FRONTEND_DEV,
                AgentRole.BACKEND_DEV,
                AgentRole.FULLSTACK_DEV,
                AgentRole.QA_ENGINEER,
            ],
            MessageType.SPRINT_PLANNING: [
                AgentRole.PRODUCT_OWNER,
                AgentRole.SCRUM_MASTER,
                AgentRole.TECH_LEAD,
            ],
            MessageType.CODE_REVIEW: [AgentRole.TECH_LEAD, AgentRole.QA_ENGINEER],
            MessageType.STANDUP_UPDATE: [AgentRole.SCRUM_MASTER],
            MessageType.REQUIREMENT_CLARIFICATION: [AgentRole.PRODUCT_OWNER],
            MessageType.ARCHITECTURE_DECISION: [AgentRole.TECH_LEAD],
        }

    def add_route(self, route: MessageRoute) -> str:
        """Add a custom routing rule."""
        route_id = str(uuid.uuid4())
        self.routes[route_id] = route
        return route_id

    def get_destinations(self, message: AgentMessage) -> list[AgentRole]:
        """Get destination agents for a message."""
        destinations = []

        # Explicit recipient
        if message.recipient:
            destinations.append(message.recipient)
        else:
            # Use routing rules
            default_recipients = self.routing_rules.get(message.message_type, [])
            destinations.extend(default_recipients)

            # Check custom routes
            for route in self.routes.values():
                if (
                    route.message_type == message.message_type
                    and route.source == message.sender
                ):
                    destinations.append(route.destination)

        # Remove sender from destinations
        destinations = [dest for dest in destinations if dest != message.sender]

        # Remove duplicates while preserving order
        seen = set()
        unique_destinations = []
        for dest in destinations:
            if dest not in seen:
                seen.add(dest)
                unique_destinations.append(dest)

        return unique_destinations


class MessageBus:
    """Central message bus for agent communication."""

    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.router = MessageRouter()
        self.validator = ProtocolValidator()

        # Message queues and handlers
        self.message_queues: dict[AgentRole, deque] = defaultdict(
            lambda: deque(maxlen=max_queue_size)
        )
        self.handlers: dict[AgentRole, list[MessageHandler]] = defaultdict(list)
        self.subscribers: dict[MessageType, list[MessageHandler]] = defaultdict(list)

        # Metrics and monitoring
        self.message_history: deque = deque(maxlen=10000)
        self.failed_messages: list[AgentMessage] = []
        self.metrics = {
            "total_messages": 0,
            "messages_by_type": defaultdict(int),
            "messages_by_sender": defaultdict(int),
            "validation_failures": 0,
            "routing_failures": 0,
        }

        self.logger = logging.getLogger("message.bus")
        self._running = False
        self._process_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the message bus."""
        self._running = True
        self._process_task = asyncio.create_task(self._process_messages())
        self.logger.info("Message bus started")

    async def stop(self) -> None:
        """Stop the message bus."""
        self._running = False
        if self._process_task:
            self._process_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._process_task
        self.logger.info("Message bus stopped")

    def register_handler(self, handler: MessageHandler) -> None:
        """Register a message handler."""
        self.handlers[handler.agent_role].append(handler)

        # Also register for subscription-based delivery
        for message_type in handler.message_types:
            self.subscribers[message_type].append(handler)

        self.logger.info(
            f"Registered handler {handler.handler_id} for {handler.agent_role.value}"
        )

    def unregister_handler(self, handler_id: str, agent_role: AgentRole) -> bool:
        """Unregister a message handler."""
        handlers = self.handlers.get(agent_role, [])
        for i, handler in enumerate(handlers):
            if handler.handler_id == handler_id:
                del handlers[i]

                # Remove from subscribers
                for message_type in handler.message_types:
                    self.subscribers[message_type] = [
                        h
                        for h in self.subscribers[message_type]
                        if h.handler_id != handler_id
                    ]

                self.logger.info(f"Unregistered handler {handler_id}")
                return True

        return False

    async def send_message(self, message: AgentMessage) -> ValidationResult:
        """Send a message through the bus."""

        # Validate message
        validation = self.validator.validate_message(message)
        if not validation.is_valid:
            self.metrics["validation_failures"] += 1
            self.failed_messages.append(message)
            self.logger.warning(f"Message validation failed: {validation.errors}")
            return validation

        # Route message
        destinations = self.router.get_destinations(message)
        if not destinations:
            validation.add_warning("No destinations found for message")
            self.metrics["routing_failures"] += 1

        # Queue message for each destination
        for destination in destinations:
            self.message_queues[destination].append(message)

        # Update metrics
        self._update_metrics(message)

        # Store in history
        self.message_history.append(
            {
                "message": message,
                "destinations": destinations,
                "timestamp": datetime.now(),
                "validation": validation,
            }
        )

        self.logger.debug(
            f"Message {message.id} queued for {len(destinations)} destinations"
        )
        return validation

    async def _process_messages(self) -> None:
        """Process messages from queues."""
        while self._running:
            try:
                # Process high-priority messages first
                await self._process_priority_messages()

                # Process regular messages
                await self._process_regular_messages()

                # Cleanup completed protocols
                self.validator.cleanup_completed_protocols()

                # Sleep briefly to prevent busy loop
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error processing messages: {e}")
                await asyncio.sleep(1.0)

    async def _process_priority_messages(self) -> None:
        """Process high-priority messages first."""
        for role, queue in self.message_queues.items():
            if not queue:
                continue

            # Check for high-priority messages
            high_priority_indices = []
            for i, message in enumerate(queue):
                if message.priority in [MessagePriority.CRITICAL, MessagePriority.HIGH]:
                    high_priority_indices.append(i)

            # Process high-priority messages first
            for i in reversed(high_priority_indices):  # Reverse to maintain queue order
                message = queue[i]
                del queue[i]  # Remove from queue
                await self._deliver_message(message, role)

    async def _process_regular_messages(self) -> None:
        """Process regular messages."""
        for role, queue in self.message_queues.items():
            if queue:
                message = queue.popleft()
                await self._deliver_message(message, role)

    async def _deliver_message(
        self, message: AgentMessage, destination: AgentRole
    ) -> None:
        """Deliver message to handlers."""
        handlers = self.handlers.get(destination, [])

        for handler in handlers:
            if handler.can_handle(message):
                try:
                    if handler.is_async:
                        await handler.callback(message)
                    else:
                        handler.callback(message)

                    self.logger.debug(
                        f"Message {message.id} delivered to {handler.handler_id}"
                    )

                except Exception as e:
                    self.logger.error(
                        f"Handler {handler.handler_id} failed to process message {message.id}: {e}"
                    )

    def _update_metrics(self, message: AgentMessage) -> None:
        """Update message metrics."""
        self.metrics["total_messages"] += 1
        self.metrics["messages_by_type"][message.message_type.value] += 1
        self.metrics["messages_by_sender"][message.sender.value] += 1

    def get_queue_status(self) -> dict[str, dict]:
        """Get status of message queues."""
        status = {}
        for role, queue in self.message_queues.items():
            status[role.value] = {
                "queue_size": len(queue),
                "handlers": len(self.handlers.get(role, [])),
                "oldest_message": queue[0].timestamp.isoformat() if queue else None,
            }
        return status

    def get_metrics(self) -> dict[str, Any]:
        """Get message bus metrics."""
        metrics = self.metrics.copy()
        metrics.update(
            {
                "active_protocols": len(self.validator.active_protocols),
                "failed_messages": len(self.failed_messages),
                "queue_sizes": {
                    role.value: len(queue)
                    for role, queue in self.message_queues.items()
                },
                "handler_count": sum(
                    len(handlers) for handlers in self.handlers.values()
                ),
            }
        )
        return metrics

    def get_recent_messages(self, limit: int = 50) -> list[dict]:
        """Get recent message history."""
        recent = list(self.message_history)[-limit:]
        return [
            {
                "id": entry["message"].id,
                "type": entry["message"].message_type.value,
                "sender": entry["message"].sender.value,
                "destinations": [dest.value for dest in entry["destinations"]],
                "timestamp": entry["timestamp"].isoformat(),
                "valid": entry["validation"].is_valid,
            }
            for entry in recent
        ]
