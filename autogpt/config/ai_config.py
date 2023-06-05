# sourcery skip: do-not-use-staticmethod
"""
A module that contains the AIConfig class object that contains the configuration
"""
from __future__ import annotations

import importlib
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Type

import distro
import yaml

if TYPE_CHECKING:
    from autogpt.commands.command import CommandRegistry
    from autogpt.prompts.generator import PromptGenerator

# Soon this will go in a folder where it remembers more stuff about the run(s)
SAVE_FILE = str(Path(os.getcwd()) / "ai_settings.yaml")


class AIConfig:
    """
    A class object that contains the configuration information for the AI

    Attributes:
        ai_name (str): The name of the AI.
        ai_role (str): The description of the AI's role.
        ai_goals (list): The list of objectives the AI is supposed to complete.
        api_budget (float): The maximum dollar value for API calls (0.0 means infinite)
    """

    def __init__(
        self,
        ai_name: str = "",
        ai_id: int = 0,
        ai_role: str = "",
        ai_goals: list | None = None,
        founder: bool = False,
        init_memory: bool = False,
        terminated: bool = False,
        loop_count: int = 0,
        agent_dir_path: str = "",
        api_budget: float = 0.0,
    ) -> None:
        """
        Initialize a class instance

        Parameters:
            ai_name (str): The name of the AI.
            ai_role (str): The description of the AI's role.
            ai_goals (list): The list of objectives the AI is supposed to complete.
            api_budget (float): The maximum dollar value for API calls (0.0 means infinite)
        Returns:
            None
        """
        if ai_goals is None:
            ai_goals = []
        self.ai_id = ai_id
        self.ai_name = ai_name
        self.ai_role = ai_role
        self.ai_goals = ai_goals
       
        self.terminated = terminated
        self.loop_count = loop_count
        
        # Implementation Specific
        self.founder = founder
        self.init_memory = init_memory
        self.agent_dir_path = agent_dir_path
        print("agent file path: ", self.agent_dir_path)
        self.agent_yaml_path = os.path.join(agent_dir_path, "agent.yaml")
        self.save()
       

    # Soon this will go in a folder where it remembers more stuff about the run(s)
    # SAVE_FILE = os.path.join(os.path.dirname(__file__), "..", "ai_settings.yaml")
    # @staticmethod
    # def load(config_file: str = SAVE_FILE) -> "AIConfig":
        self.api_budget = api_budget
        self.prompt_generator: PromptGenerator | None = None
        self.command_registry: CommandRegistry | None = None

    #@staticmethod
    #def load(config_file: str = SAVE_FILE) -> "AIConfig":
       

    @classmethod
    def load(cls, file_path):
        """
            Returns class object with parameters (ai_name, ai_role, ai_goals, api_budget) loaded from
            yaml file if yaml file exists,
            else returns class with no parameters.

            Parameters:
            config_file (int): The path to the direcotry of the.
                DEFAULT: "../ai_settings.yaml"
        

            Returns:
                cls (object): An instance of given cls object
        """
        try:
            with open(file_path) as file:
                config_params = yaml.load(file, Loader=yaml.FullLoader)
                instance = cls(file_path=str(file_path), **config_params)
                return instance
        except FileNotFoundError:
            return None

    def remove(self):
        if os.path.exists(self.agent_yaml_path):
            os.remove(self.agent_yaml_path)

        if os.path.exists(self.agent_dir_path):
            os.remove(self.agent_dir_path)
        else:
            print(
                f"Can't remove agent: {self.ai_name} as couldn't find file: {self.agent_yaml_path}."
            )

    def save(self):
        
        print("agent dire path", self.agent_dir_path)
        print("agent yaml_path", self.agent_yaml_path)
        if not os.path.exists(Path(self.agent_dir_path)):
            os.makedirs(Path(self.agent_dir_path), exist_ok=True)


        config = {attr: getattr(self, attr) for attr in vars(self)}
        config.pop("file", None)  # Exclude file attribute
        with open(self.agent_yaml_path, "w") as file:
            yaml.dump(config, file)

    def construct_full_prompt(self, organization, prompt_generator: Optional[PromptGenerator] = None, ) -> str:
        """
        Returns a prompt to the user with the class information in an organized fashion.

        Parameters:
            None

        Returns:
            full_prompt (str): A string containing the initial prompt for the user
              including the ai_name, ai_role, ai_goals, and api_budget.
        """

        prompt_start = (
            "Your decisions must always be made independently without"
            " seeking user assistance. Play to your strengths as an LLM and pursue"
            " simple strategies with no legal complications."
            ""
        )

        from autogpt.config import Config
        from autogpt.prompts.prompt import build_default_prompt_generator

        cfg = Config()
        if prompt_generator is None:
            prompt_generator = build_default_prompt_generator()
        prompt_generator.goals = self.ai_goals
        prompt_generator.name = self.ai_name
        prompt_generator.role = self.ai_role
        prompt_generator.command_registry = self.command_registry
        for plugin in cfg.plugins:
            if not plugin.can_handle_post_prompt():
                continue
            prompt_generator = plugin.post_prompt(prompt_generator)

        if cfg.execute_local_commands:
            # add OS info to prompt
            os_name = platform.system()
            os_info = (
                platform.platform(terse=True)
                if os_name != "Linux"
                else distro.name(pretty=True)
            )

            prompt_start += f"\nThe OS you are running on is: {os_info}"

        if self.founder:
            print('founder')
            full_prompt = (
                f"You are {self.ai_name}, founder of organization {organization.name}. your role is: {self.ai_role}\n{prompt_start}.\n\nGOALS:\n\n"
            )
        else:
            print('not founder')
            s_id, s_name = organization.get_supervisor_info(self.ai_id)
            full_prompt = (
                f"you are {self.ai_name}, member of organization {organization.name}. Your supervisor is Id:{s_id} Name:{s_name}.\n" + 
                f"Your role is: {self.ai_role}\n{prompt_start}.\n\nGOALS:\n\n"   
            )

        # Construct full prompt
        full_prompt = f"You are {prompt_generator.name}, {prompt_generator.role}\n{prompt_start}\n\nGOALS:\n\n"
        for i, goal in enumerate(self.ai_goals):
            print(self.ai_goals)
            full_prompt += f"{i+1}. {goal}\n"
        if self.api_budget > 0.0:
            full_prompt += f"\nIt takes money to let you run. Your API budget is ${self.api_budget:.3f}"
        self.prompt_generator = prompt_generator
        full_prompt += f"\n\n{prompt_generator.generate_prompt_string()}"
        return full_prompt
