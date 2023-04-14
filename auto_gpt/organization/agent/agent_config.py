import os

import yaml

from auto_gpt.prompt import get_prompt

DEF_EMPLOYEE_DESCRIPTION = """You are an employee of {agent_supervisor}. You are tasked with: {agent_task}."""

class AgentConfig(object):
    def __init__(
        self,
        file_path,
        name,
        agent_id,
        task,
        goals,
        budget,
        operating_cost=0,
        status=None,
        supervisor_name=None,
        supervisor_id=None,
        founder=False,
        pending_messages=None,
        init_memory=True,
    ):
        self.file = file_path
        self.agent_id = agent_id
        self.name = name
        self.task = task
        self.goals = goals
        self.status = status
        self.budget = budget
        self.operating_cost = operating_cost
        self.supervisor_name = supervisor_name
        self.supervisor_id = supervisor_id
        self.founder = founder
        self.pending_messages = pending_messages or []
        self.init_memory = init_memory

        self.save()

    @classmethod
    def load(cls, file_path):
        try:
            with open(file_path) as file:
                config_params = yaml.load(file, Loader=yaml.FullLoader)
                instance = cls(file_path, **config_params)
                return instance
        except FileNotFoundError:
            return None

    def remove(self):
        if os.path.exists(self.file):
            os.remove(self.file)
        else:
            print(
                f"Can't remove agent: {self.name} as couldn't find file: {self.file}."
            )

    def save(self):
        os.makedirs(os.path.dirname(self.file), exist_ok=True)
        config = {attr: getattr(self, attr) for attr in vars(self)}
        config.pop("file", None)  # Exclude file attribute
        with open(self.file, "w") as file:
            yaml.dump(config, file)


    def construct_full_prompt(self) -> str:
        """
        Returns a prompt to the user with the class information in an organized fashion.
        Parameters:
            None
        Returns:
            full_prompt (str): A string containing the initial prompt for the user including the ai_name, ai_role and ai_goals.
        """

        prompt_start = """Your decisions must always be made independently without seeking user assistance. Play to your strengths as an LLM and pursue simple strategies with no legal complications."""
 
        # Construct full prompt
      
        full_prompt = f""
        if self.founder:
            full_prompt += f"You are {self.name}, {self.task}\n{prompt_start}\n\nGOALS:{str(self.goals)}\n\n"
        else:
            full_prompt += f"You are an employee of {self.supervisor_name}. You are {self.name}, and tasked with {self.task}\n\nGOALS:{str(self.goals)}\n\n"
        

        full_prompt += f"\n\n{get_prompt(self.budget, self.operating_cost)}"
        print("\n\n" , full_prompt, "\n\n")
        return full_prompt

