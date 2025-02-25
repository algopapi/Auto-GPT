""" A module for generating custom prompt strings."""
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from autogpt.json_utils.utilities import llm_response_schema

if TYPE_CHECKING:
    from autogpt.commands.command import CommandRegistry


class PromptGenerator:
    """
    A class for generating custom prompt strings based on constraints, commands,
        resources, and performance evaluations.
    """

    def __init__(self) -> None:
        """
        Initialize the PromptGenerator object with empty lists of constraints,
            commands, resources, and performance evaluations.
        """
        self.constraints = [
            "YOUR CAPABILITIES ARE LIMITED: You have to subdivide complex task into smaller task for which you hir employees to complete them "
            "YOUR CONSTRAINTS: Your supervisor has given you a budget. Each step will cost you 100$ for yourself and each employee. If you have 5 employees, each step will cost you 600$.",
            "YOUR CONSTRAINTS: Complete your task before you run out of budget. Simple tasks will take you/your employees 10 steps so account for this when budgeting your employees",
        ]
        self.commands = []
        self.resources = [
            "YOUR STAFF: Here is a list of your staff members, their roles, current spending, and their current engagement.",
            "YOUR INBOX: Your inbox contains incoming emails that need to be responded to. Prioritize your inbox by responding to the most important emails first.",
            "YOUR BUDGET: Your budget displays: 1) your current budget - allocated by your supervisor. 2) your current spending each step (100$ for each employee) - how much you have spent so far. 3) Remaining steps: how many more steps you have left to complete the project.",
        ]

        self.performance_evaluation = [
            "DELIVERIES: Your supervisor will evaluate you based on if you and your team manage to complete the assigend task.",
        ]
        self.goals = []
        self.command_registry: CommandRegistry | None = None
        self.name = "Bob"
        self.role = "AI"

    def add_constraint(self, constraint: str) -> None:
        """
        Add a constraint to the constraints list.

        Args:
            constraint (str): The constraint to be added.
        """
        self.constraints.append(constraint)

    def add_command(
        self,
        command_label: str,
        command_name: str,
        args=None,
        function: Optional[Callable] = None,
    ) -> None:
        """
        Add a command to the commands list with a label, name, and optional arguments.

        Args:
            command_label (str): The label of the command.
            command_name (str): The name of the command.
            args (dict, optional): A dictionary containing argument names and their
              values. Defaults to None.
            function (callable, optional): A callable function to be called when
                the command is executed. Defaults to None.
        """
        if args is None:
            args = {}

        command_args = {arg_key: arg_value for arg_key, arg_value in args.items()}

        command = {
            "label": command_label,
            "name": command_name,
            "args": command_args,
            "function": function,
        }

        self.commands.append(command)

    def _generate_command_string(self, command: Dict[str, Any]) -> str:
        """
        Generate a formatted string representation of a command.

        Args:
            command (dict): A dictionary containing command information.

        Returns:
            str: The formatted command string.
        """
        args_string = ", ".join(
            f'"{key}": "{value}"' for key, value in command["args"].items()
        )
        return f'{command["label"]}: "{command["name"]}", args: {args_string}'

    def add_resource(self, resource: str) -> None:
        """
        Add a resource to the resources list.

        Args:
            resource (str): The resource to be added.
        """
        self.resources.append(resource)

    def add_performance_evaluation(self, evaluation: str) -> None:
        """
        Add a performance evaluation item to the performance_evaluation list.

        Args:
            evaluation (str): The evaluation item to be added.
        """
        self.performance_evaluation.append(evaluation)

    def _generate_numbered_list(self, items: List[Any], item_type="list") -> str:
        """
        Generate a numbered list from given items based on the item_type.

        Args:
            items (list): A list of items to be numbered.
            item_type (str, optional): The type of items in the list.
                Defaults to 'list'.

        Returns:
            str: The formatted numbered list.
        """
        if item_type == "command":
            command_strings = []
            if self.command_registry:
                command_strings += [
                    str(item)
                    for item in self.command_registry.commands.values()
                    if item.enabled
                ]
            # terminate command is added manually
            command_strings += [self._generate_command_string(item) for item in items]
            return "\n".join(f"{i+1}. {item}" for i, item in enumerate(command_strings))
        else:
            return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

    def generate_prompt_string(self) -> str:
        """
        Generate a prompt string based on the constraints, commands, resources,
            and performance evaluations.

        Returns:
            str: The generated prompt string.
        """
        return (
            f"Constraints:\n{self._generate_numbered_list(self.constraints)}\n\n"
            "Commands:\n"
            f"{self._generate_numbered_list(self.commands, item_type='command')}\n\n"
            f"Resources:\n{self._generate_numbered_list(self.resources)}\n\n"
            "Performance Evaluation:\n"
            f"{self._generate_numbered_list(self.performance_evaluation)}\n\n"
            "Respond with only valid JSON conforming to the following schema: \n"
            f"{llm_response_schema()}\n"
        )
