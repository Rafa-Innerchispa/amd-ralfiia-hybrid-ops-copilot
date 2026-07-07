"""Re-export A2A schemas for backend consumers."""

from shared.a2a_protocol import (
    A2AMessage,
    A2AMessagePart,
    A2ATaskRequest,
    A2ATaskResponse,
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Order,
    OrderItem,
    ResponseFormat,
    RoutingEvent,
)

__all__ = [
    "ResponseFormat",
    "OrderItem",
    "Order",
    "AgentSkill",
    "AgentAuthentication",
    "AgentCapabilities",
    "AgentCard",
    "A2AMessagePart",
    "A2AMessage",
    "A2ATaskRequest",
    "A2ATaskResponse",
    "RoutingEvent",
]
