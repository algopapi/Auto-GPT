import os

import yaml


class AgentConfig(object):
    def __init__(
        self,
        file_path,
        name,
        agent_id,
        task,
        goals,
        status=None,
        supervisor_name=None,
        supervisor_id=None,
        founder=False,
    ):
        self.file = file_path
        self.agent_id = agent_id
        self.name = name
        self.task = task
        self.goals = goals
        self.status = status
        self.supervisor_name = supervisor_name
        self.supervisor_id = supervisor_id
        self.founder = founder
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
        config.pop("file", None)  # Exclue file attribute
        with open(self.file, "w") as file:
            yaml.dump(config, file)
