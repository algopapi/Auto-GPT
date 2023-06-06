"""Commands for converting audio to text."""
import json
from typing import TYPE_CHECKING

import requests

from autogpt.commands.command import command
from autogpt.config import Config

if TYPE_CHECKING:
    from autogpt.config import Config


@command(
    "message_staff",
    "Message an employee",
    '"agent_id" : "<agent_id>", "message" : "<message>"',
    enabled=True, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
def message_staff(agent_id: str, message: str, config: Config) -> str:
    pass
    
@command(
    "message_supervisor",
    "Message your supervisor",
    '"message" : "<message to supervisor>"',
    enabled=True, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
def message_supervisor(agent_id: str, message: str, config: Config) -> str:
    pass

@command(
    "hire_staff", 
    "Hire a staff member as an employee",
    '"name":"<name>", "role": "<role of the hired employee>", "goals": "<list of employee goals (comma seperated)>", "budget": "<assign budget to employee (the max amount budget the employee is allowed to spend))>"',
    enabled=True,
    disabled_reason="not an organization"
)   
def hire_staff(name: str, role: str, goals: str, budget: str, config: Config) -> str:
    pass

@command(
    'fire_staff',
    'Fire a staff member',
    '"agent_id":"<id of staff member to fire>"',
    enabled=True,
    disabled_reason="not an organization"
)
def fire_staff(agent_id: str, config: Config) -> str:
    pass