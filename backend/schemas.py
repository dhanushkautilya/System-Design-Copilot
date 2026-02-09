from __future__ import annotations

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class InputPayload(BaseModel):
    # Mandatory core fields
    app_name: str
    description: str = Field(..., description="High-level description of what the app does")
    dau: int = Field(..., ge=1, description="Daily active users")
    peak_rps: int = Field(..., ge=1, description="Peak requests per second")
    read_write_ratio: float = Field(..., gt=0, description="Read/Write ratio (e.g., 5 for 5:1 read/write)")
    regions: List[str] = Field(default_factory=lambda: ["us-east"], description="Geographic regions")
    budget_level: str = Field(default="medium", description="Budget level: low, medium, or high")

    # Optional additional fields
    domain: Optional[str] = Field(None, description="Domain e.g. fintech, health, ecom")
    end_users: Optional[str] = Field(None, description="consumer, internal, b2b")
    user_roles: List[str] = Field(default_factory=list)
    peak_concurrent_users: Optional[int] = Field(None, ge=1)
    traffic_pattern: str = Field(default="steady")
    data_types: List[str] = Field(default_factory=list)
    compliance: List[str] = Field(default_factory=list)
    latency_target_ms_p50: Optional[int] = Field(None, ge=1)
    latency_target_ms_p95: Optional[int] = Field(None, ge=1)
    availability_target: Optional[float] = Field(None, ge=0.9, le=1.0)
    rpo_hours: Optional[float] = Field(None, ge=0)
    rto_hours: Optional[float] = Field(None, ge=0)
    apis_needed: List[str] = Field(default_factory=list)
    api_rate_limits_rpm: Optional[int] = Field(None, ge=0)
    team_size: Optional[int] = Field(None, ge=1)
    special_constraints: List[str] = Field(default_factory=list)

    @field_validator("budget_level")
    def validate_budget(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"budget_level must be one of {allowed}")
        return v

    @field_validator("traffic_pattern")
    def validate_pattern(cls, v: str) -> str:
        allowed = {"steady", "spiky"}
        if v not in allowed:
            raise ValueError(f"traffic_pattern must be one of {allowed}")
        return v


class ReportSection(BaseModel):
    title: str
    bullets: List[str]


class APIExample(BaseModel):
    method: str
    path: str
    description: str
    request: dict
    response: dict
    rate_limit_rpm: Optional[int]
    idempotent: bool


class OutputPayload(BaseModel):
    submission_id: Optional[int] = None
    summary: str
    assumptions: List[str]
    architecture_options: List[ReportSection]
    recommended_option: str
    tech_stack: List[str]
    sizing: dict
    api_design: List[APIExample]
    performance_plan: List[str]
    security_plan: List[str]
    reliability_plan: List[str]
    risks: List[str]
    phased_rollout: List[str]
    mermaid_flow: str
    mermaid_components: str
    observability: List[str]
    threat_model: List[str]


class SubmissionResponse(BaseModel):
    id: int
    created_at: str
    title: str
    input: InputPayload
    output: OutputPayload


class SubmissionListResponse(BaseModel):
    submissions: List[SubmissionResponse]
