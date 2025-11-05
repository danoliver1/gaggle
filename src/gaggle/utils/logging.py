"""Structured logging configuration for Gaggle."""

import sys
from typing import Any, Dict, Optional
import structlog
from structlog.typing import EventDict

from ..config.settings import settings


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add timestamp to log events."""
    import datetime
    event_dict["timestamp"] = datetime.datetime.utcnow().isoformat()
    return event_dict


def add_level(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to log events."""
    event_dict["level"] = method_name.upper()
    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    processors = [
        add_timestamp,
        add_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if settings.structured_logging:
        # JSON output for structured logging
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Human-readable output for development
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])
    
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add structured logging to classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)
    
    def log_event(self, event: str, **kwargs: Any) -> None:
        """Log an event with additional context."""
        self.logger.info(event, **kwargs)