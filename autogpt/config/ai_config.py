# sourcery skip: do-not-use-staticmethod
"""
A module that contains the AIConfig class object that contains the configuration
"""
from __future__ import annotations

import importlib
import os
from typing import Type

import yaml

import permanent_storage


class AIConfig:
    """
    A class object that contains the configuration information for the AI

    Attributes:
        ai_name (str): The name of the AI.
        ai_role (str): The description of the AI's role.
        ai_goals (list): The list of objectives the AI is supposed to complete.
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
        file_path: str = "",
    ) -> None:
        """
        Initialize a class instance

        Parameters:
            ai_name (str): The name of the AI.
            ai_role (str): The description of the AI's role.
            ai_goals (list): The list of objectives the AI is supposed to complete.
        Returns:
            None
        """
        if ai_goals is None:
            ai_goals = []
        self.ai_id = ai_id
        self.ai_name = ai_name
        self.ai_role = ai_role
        self.ai_goals = ai_goals
        self.founder = founder
        self.terminated = terminated
        self.loop_count = loop_count
        
        # Implementation Specific
        self.init_memory = init_memory
        self.file = file_path
        print("init file path: ", file_path)
        self.save()
       

    # Soon this will go in a folder where it remembers more stuff about the run(s)
    # SAVE_FILE = os.path.join(os.path.dirname(__file__), "..", "ai_settings.yaml")

    # @staticmethod
    # def load(config_file: str = SAVE_FILE) -> "AIConfig":

    @classmethod
    def load(cls, file_path):
        try:
            with open(file_path) as file:
                config_params = yaml.load(file, Loader=yaml.FullLoader)
                instance = cls(file_path=str(file_path), **config_params)
                return instance
        except FileNotFoundError:
            return None

    def remove(self):
        file_path = self.file

        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(
                f"Can't remove agent: {self.ai_name} as couldn't find file: {file_path}."
            )

    def save(self):
        file_path = self.file
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        config = {attr: getattr(self, attr) for attr in vars(self)}
        config.pop("file", None)  # Exclude file attribute
        with open(file_path, "w") as file:
            yaml.dump(config, file)

    def construct_full_prompt(self) -> str:
        """
        Returns a prompt to the user with the class information in an organized fashion.

        Parameters:
            None

        Returns:
            full_prompt (str): A string containing the initial prompt for the user
              including the ai_name, ai_role and ai_goals.
        """

        prompt_start = (
            "Your decisions must always be made independently without"
            " seeking user assistance. Play to your strengths as an LLM and pursue"
            " simple strategies with no legal complications."
            ""
        )

        from autogpt.prompt import get_prompt

        # Construct full prompt
        full_prompt = (
            f"You are {self.ai_name}, {self.ai_role}\n{prompt_start}\n\nGOALS:\n\n"
        )
        for i, goal in enumerate(self.ai_goals):
            full_prompt += f"{i+1}. {goal}\n"

        full_prompt += f"\n\n{get_prompt()}"
        return full_prompt
