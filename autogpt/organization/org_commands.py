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


@command(
    "message_agent",
    "Message an agent in the organization",
    '"receiver_id" : "<receiver_id>", "message" : "<message>"',
    enabled=True, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
async def message_agent(receiver_id: str, message: str, config: Config, agent: Agent) -> str:
    """Messages a staff member (employee) with a given message. 

        Args:
            agent_id (str): The ID of the receiver
            message (str): The message to send to the receiver

        Returns:
            str: Send confirmation or error
    """
    event_id = await agent.send_event("message_agent", agent.ai_id, receiver_id, message)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
        "get_conversation_history",
        "Get the conversation history between you and an agent",
        '"agent_id" : "<agent_id of message respondent>"',
)
async def get_conversation_history(agent_id: str, config: Config, agent: Agent) -> str:
    """Gets the conversation history between you and an agent. 

        Args:
            agent_id (str): The ID of the agent to get the conversation history with

        Returns:
            str: The conversation history
    """
    event_id = await agent.send_event("get_conversation_history", agent.ai_id, agent_id)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
        "respond_to_message",
        "Respond to a message from an agent in your inbox",
        '"message_id" : "<message_id of message you want to respond to>"',
)
async def respond_to_message(message_id: str, config: Config, agent: Agent) -> str:
    """Gets the conversation history between you and an agent. 

        Args:
            agent_id (str): The ID of the agent to get the conversation history with

        Returns:
            str: The conversation history
    """
    event_id = await agent.send_event("get_conversation_history", agent.ai_id, agent_id)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
    "hire_staff", 
    "Hire a staff member as an employee",
    '"staff_name":"<staff_name>", "role": "<role of the hired employee>", "goals": "<list of employee goals (comma seperated)>", "budget": "<assign budget to employee (the max amount budget the employee is allowed to spend))>"',
    enabled=True,
    disabled_reason="not an organization"
)  
async def hire_staff(staff_name: str, role: str, goals: str, budget: str, config: Config, agent: Agent) -> str:
    """Hires a staff member into the organization as an employee. 

        Args:
            staff_name (str): The name of the staff member to hire
            role (str): The role of the staff member to hire
            goals (str): The goals of the staff member to hire
            budget (str): The budget of the staff member to hire

        Returns:
            str: confirmation or error
    """
    event_id = await agent.send_event("hire_staff", staff_name, role, goals, budget, agent.ai_id)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
    'fire_staff',
    'Fire a staff member',
    '"agent_id":"<id of staff member to fire>"',
    enabled=True,
    disabled_reason="not an organization"
)
async def fire_staff(agent_id: str, config: Config, agent: Agent) -> str:
    """Fires a staff member from the organization.
        Args:
            agent_id (str): The ID of the staff member to fire

        Returns:
            str: confirmation or error
    """
    event_id = await agent.send_event("fire_staff", agent_id)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
    "message_supervisor",
    "Message your supervisor",
    '"message" : "<message to supervisor>"',
    enabled=False, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
async def message_supervisor( message: str, config: Config, agent: Agent) -> str:
    """Messages a employees supervisor with a given message. 

        Args:
            message (str): The message to send to the supervsiro

        Returns:
            str: Send confirmation or error
    """
    event_id = await agent.send_event("message_supervisor",agent.ai_id, message)
    response = await agent.organization.get_event_result(event_id)
    return response


@command(
    "message_staff",
    "Message an agent in the organization",
    '"receiver_id" : "<receiver_id>", "message" : "<message>"',
    enabled=False, # change this to be dependent on whether the user is running org mode
    disabled_reason="not an organization"
)
async def message_staff(receiver_id: str, message: str, config: Config, agent: Agent) -> str:
    """Messages a staff member (employee) with a given message. 

        Args:
            agent_id (str): The ID of the receiver
            message (str): The message to send to the receiver

        Returns:
            str: Send confirmation or error
    """
    event_id = await agent.send_event("message_staff", agent.ai_id, receiver_id, message)
    response = await agent.organization.get_event_result(event_id)
    return response