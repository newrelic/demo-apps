"""
Pydantic models for AI Agent requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


class ToolCall(BaseModel):
    """Record of a tool invocation."""
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    success: bool
    result: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class RepairResult(BaseModel):
    """Result from a repair workflow execution."""
    success: bool
    actions_taken: List[str]
    containers_restarted: List[str] = Field(default_factory=list)
    final_status: str
    model_used: str
    latency_seconds: float
    tool_calls: List[ToolCall] = Field(default_factory=list)
    ai_reasoning: Optional[str] = None  # LLM analysis/reasoning for why tools were selected
    timestamp: datetime = Field(default_factory=datetime.now)


class ChatRequest(BaseModel):
    """Request for chat interaction."""
    message: str
    model: Literal["a", "b"] = "a"


class ChatResponse(BaseModel):
    """Response from chat interaction."""
    response: str
    model_used: str
    latency_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)


class ModelMetrics(BaseModel):
    """Metrics for a specific model."""
    model_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_seconds: float = 0.0
    total_tokens: int = 0  # Placeholder for future token tracking


class ComparisonResult(BaseModel):
    """Side-by-side comparison of two models."""
    model_a_result: Optional[RepairResult] = None
    model_b_result: Optional[RepairResult] = None
    winner: Optional[str] = None  # "a", "b", or "tie"
    reason: str = ""


class AgentStatus(BaseModel):
    """Current status of the AI Agent service."""
    status: str = "running"
    model_a_metrics: ModelMetrics
    model_b_metrics: ModelMetrics
    uptime_seconds: float
