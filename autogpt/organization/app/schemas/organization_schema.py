from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class OrganizationBase(BaseModel):
    name: str
    initial_budget: int
    id_count: int
    goal: str
    agent_budgets: Dict[int, int]
    agent_running_costs: Dict[int, int]
    agent_statuses: Dict[int, str]
    agent_termination_events: Dict[int, str]
    supervisor_to_staff: Dict[int, List[int]]


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    initial_budget: Optional[int] = None
    id_count: Optional[int] = None
    goal: Optional[str] = None
    agent_budgets: Optional[Dict[int, int]] = None
    agent_running_costs: Optional[Dict[int, int]] = None
    agent_statuses: Optional[Dict[int, str]] = None
    agent_termination_events: Optional[Dict[int, str]] = None
    supervisor_to_staff: Optional[Dict[int, List[int]]] = None


class Organization(OrganizationBase):
    id: UUID

    class Config:
        orm_mode = True
