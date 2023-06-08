"""Commands for converting audio to text."""
import json
from typing import TYPE_CHECKING, Union

import requests

from autogpt.agent.agent import Agent
from autogpt.commands.command import command
from autogpt.config import Config
from autogpt.organization.organization import Organization

if TYPE_CHECKING:
    from autogpt.config import Config


async def get_agent_by_id(id: str, organization) -> Union[Agent, str]:
    agent_id = int(id)
    if agent_id in organization.agents:
        return organization.agents[agent_id]
    else:
        return "Check if you passed your ID correctly"

@command(
    "message_staff",
    "Message an employee",
    '"your_id": <your_id>", "receiver_id" : "<receiver_id>", "message" : "<message>"',
    enabled=True, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
async def message_staff(agent_id: str, message: str, config: Config) -> str:
    pass
    
@command(
    "message_supervisor",
    "Message your supervisor",
    '"your_id": <your_id>", "message" : "<message to supervisor>"',
    enabled=True, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
async def message_supervisor(agent_id: str, message: str, config: Config) -> str:
    pass

@command(
    "hire_staff", 
    "Hire a staff member as an employee",
    '"id": <your_id>", "staff_name":"<staff_name>", "role": "<role of the hired employee>", "goals": "<list of employee goals (comma seperated)>", "budget": "<assign budget to employee (the max amount budget the employee is allowed to spend))>"',
    enabled=True,
    disabled_reason="not an organization"
)   
async def hire_staff(id: str, staff_name: str, role: str, goals: str, budget: str, config: Config, agent) -> str:
    org = Organization()
    print(" hiring staff with agent = ", agent.ai_name)
    agent_or_error = await get_agent_by_id(id, org)


    if isinstance(agent_or_error, Agent):
        agent = agent_or_error # we have the correct agent.
        event_id = await agent.send_event("hire_staff", staff_name, role,goals, budget, agent.ai_name, agent.ai_id)
        response = await agent.organization.get_event_result(event_id)
        return response
    # Create a function that casts id to int and checks if it exists in the org, if so, return the agent corresponsidn to that id
    # if not, return "check if you passed your id correctly"
    else:
        print("Some sort of ID error")
        # invalid id, return error message
        return f"you passed an invalid ID as your own id. please check if you passed your id correctly and try again."



@command(
    'fire_staff',
    'Fire a staff member',
    '"agent_id":"<id of staff member to fire>"',
    enabled=True,
    disabled_reason="not an organization"
)
async def fire_staff(agent_id: str, config: Config) -> str:
    pass