"""Google A2A protocol types — shared across all RalfIIA AMD agents."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ResponseFormat(BaseModel):
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


class OrderItem(BaseModel):
    name: str
    quantity: int
    price: int


class Order(BaseModel):
    order_id: str
    status: str
    order_items: List[OrderItem]


class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: List[str] = Field(default_factory=list)
    examples: List[str] = Field(default_factory=list)


class AgentAuthentication(BaseModel):
    schemes: List[str] = Field(default_factory=lambda: ["Bearer"])


class AgentCapabilities(BaseModel):
    pushNotifications: bool = True
    streaming: bool = False


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    authentication: AgentAuthentication
    defaultInputModes: List[str] = Field(default_factory=lambda: ["text", "text/plain"])
    defaultOutputModes: List[str] = Field(default_factory=lambda: ["text", "text/plain"])
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    skills: List[AgentSkill]


class A2AMessagePart(BaseModel):
    text: str
    type: str = "text"


class A2AMessage(BaseModel):
    role: str = "user"
    parts: List[A2AMessagePart]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class A2ATaskRequest(BaseModel):
    id: str
    sessionId: str
    message: A2AMessage
    acceptedOutputModes: List[str] = Field(default_factory=lambda: ["text", "text/plain"])


class A2ATaskResponse(BaseModel):
    id: str
    sessionId: str
    status: Literal["submitted", "working", "completed", "failed", "input_required"]
    message: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_client_dict(self) -> Dict[str, Any]:
        """Unified client response (Google ADK mapping)."""
        complete = self.status == "completed"
        needs_input = self.status == "input_required"
        return {
            "is_task_complete": complete,
            "require_user_input": needs_input,
            "content": self.message or "",
            "status": self.status,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }


class RoutingEvent(BaseModel):
    ts: str
    agent: str
    runtime: str
    model: str
    tokens_local: int = 0
    tokens_remote: int = 0
    decision: str
    session_id: str = ""
