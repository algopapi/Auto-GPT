from typing import Dict, Optional
from uuid import UUID

from app.schemas.organization_schema import Organization
from pydantic import BaseModel


class AgentBase(BaseModel):
    ai_goals: Dict[str, str]
    ai_name: str
    ai_role: str
    api_budget: float
    file_path: str
    founder: bool
    init_memory: bool
    loop_count: int
    organization_goal: str
    organization_name: str
    terminated: bool
    organization_id: Optional[UUID]  # Use str for uuid type
    organization: Optional[Organization] # Optional Organizatoin Model


class AgentCreate(AgentBase):
    pass  # All fields from AgentBase are necessary for creating an Agent


class AgentRead(AgentBase):
    id: str  # Include id in the AgentRead model


class AgentUpdate(BaseModel):  # Inherits directly from BaseModel
    ai_goals: Optional[Dict[str, str]]
    ai_name: Optional[str]
    ai_role: Optional[str]
    api_budget: Optional[float]
    file_path: Optional[str]
    founder: Optional[bool]
    init_memory: Optional[bool]
    loop_count: Optional[int]
    organization_goal: Optional[str]
    organization_name: Optional[str]
    terminated: Optional[bool]
    organization_id: Optional[str]  # Allow updating organization_id
    organization: Optional[Organization] # Optional Organizatoin Model


class Agent(AgentBase):
    id: UUID

    class Config:
        orm_mode = True
