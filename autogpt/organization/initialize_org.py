import importlib.resources
import os

from colorama import Fore, Style

import permanent_storage as storage
from autogpt.logs import Logger
from autogpt.organization.organization import Organization

logger = Logger()

async def get_organization(should_speak=False):
    organizations_folder = importlib.resources.files(storage) / "organizations"
    organizations = os.listdir(organizations_folder)
    if organizations:
        logger.typewriter_log(
            "Welcome back! ",
            Fore.GREEN,
            f"these are the existing organizations: {organizations}",
            speak_text=should_speak,
        )
        should_continue = input(
            "Do you want to continue running any of the existing ones? (y/n): "
        )
        if should_continue.lower() == "y":
            name = input("Please specify the name of the existing organization: ")
            if name in organizations:
                return await Organization.load(name)
            else:
                print(
                    f"Organization with name: {name} doesn't exist, stopping execution..."
                )
    return await create_new_org(should_speak)


async def create_new_org(should_speak=False):
    ai_name = ""
    logger.typewriter_log(
        "Welcome to Auto-GPT.",
        Fore.GREEN,
        "Let's start the creation of a new organization",
        speak_text=should_speak,
    )
    logger.typewriter_log(
        "Enter a name for the organization: ",
        Fore.GREEN,
        "For example, 'ClosedAI'",
    )
    org_name = input("Organization name: ")
    if org_name == "":
        org_name = "ClosedAI"

    logger.typewriter_log(
        "Name the org founder: ", Fore.GREEN, "For example, 'Elon Musk'"
    )
    ai_name = input("Founder name: ")
    if ai_name == "":
        ai_name = "Elon Musk"

    logger.typewriter_log(
        f"{ai_name} here!",
        Fore.LIGHTBLUE_EX,
        "I am at your service.",
        speak_text=should_speak,
    )

    # Get AI Role from User
    logger.typewriter_log(
        f"Describe {ai_name}'s role: ",
        Fore.GREEN,
        "For example, 'an AI designed to autonomously develop and run businesses with the sole goal of increasing your net worth.'",
    )
    ai_role = input(f"{ai_name} is: ")
    if ai_role == "":
        ai_role = "an AI designed to autonomously develop and run businesses with the sole goal of increasing your net worth."

    # Enter up to 5 goals for the AI
    logger.typewriter_log(
        f"Enter up to 5 goals for {ai_name}: ",
        Fore.GREEN,
        "For example: \nIncrease net worth, Grow Twitter Account, Develop and manage multiple businesses autonomously'",
    )
    print(
        "Enter nothing to load defaults, enter nothing when finished.",
        flush=True,
    )
    ai_goals = []
    for i in range(5):
        ai_goal = input(f"{Fore.LIGHTBLUE_EX}Goal{Style.RESET_ALL} {i+1}: ")
        if ai_goal == "":
            break
        ai_goals.append(ai_goal)
    if len(ai_goals) == 0:
        ai_goals = [
            "Increase net worth",
            "Grow Twitter Account",
            "Develop and manage multiple businesses autonomously",
        ]
    initial_budget = 50000
    new_organization = await Organization.create(org_name, initial_budget)
    await new_organization.create_agent(
        name=ai_name, role=ai_role, goals=ai_goals, founder=True, budget=initial_budget
    )
    return new_organization
