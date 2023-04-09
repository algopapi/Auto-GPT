from typing import Dict, List
from colorama import Fore, Style
import importlib.resources
import glob
import os

from .agent import Agent, AgentConfig
from auto_gpt.utils.print_utils import print_to_console
import permanent_storage


# An organization of multiple agent.
class Organization:
    def __init__(self, name):
        self.name = name
        self.agents: Dict[int, Agent] = {}

    @classmethod
    def load(cls, organization_name):
        organization_folder = (
            importlib.resources.files(permanent_storage)
            / f"organizations/{organization_name}"
        )

        org = Organization(organization_name)
        agent_files = glob.glob(os.path.join(str(organization_folder), "*.yaml"))

        # Create all the agents
        for file_path in agent_files:
            agent_config = AgentConfig.load(file_path)
            if agent_config is not None:
                org.add_agent(agent_config)
        # Add staff to supervisor
        for _, agent in org.agents.items():
            if not agent.cfg.founder:
                supervisor = org.agents[agent.cfg.supervisor_name]
                if supervisor is not None:
                    supervisor.add_staff(agent)
        return org

    def run(self):
        while True:
            agents_list = list(self.agents.values())

            for agent in agents_list:
                print(
                    Fore.GREEN
                    + f"\n ---------------- Running agent {agent.cfg.name} -----------------\n"
                    + Style.RESET_ALL,
                    end="",
                )
                agent.step()

    def create_agent(
        self,
        name,
        task,
        goals,
        supervisor_name=None,
        founder=False,
    ):
        organization_file = (
            importlib.resources.files(permanent_storage)
            / f"organizations/{self.name}/{name}.yaml"
        )
        agent_cfg = AgentConfig(
            file_path=organization_file,
            name=name,
            task=task,
            goals=goals,
            supervisor_name=supervisor_name,
            founder=founder,
        )
        return self.add_agent(agent_cfg)

    def add_agent(self, agent_cfg):
        new_agent = Agent(organization=self, agent_config=agent_cfg)
        self.agents[new_agent.cfg.name] = new_agent
        return new_agent

    def remove_agent(self, name):
        if name in self.agents:
            agent = self.agents[name]
            agent.cfg.remove()
            del self.agents[name]
            return True
        else:
            return False

    def route_message(self, sender, reciever, message):
        print_to_console(
            "ORG: Route message",
            Fore.RED,
            f"ORG: Sender: {sender.name} \n ORG: Reciever: {reciever.name} \n ORG: Message: {message} \n",
        )
        reciever.recieve_message(sender, message)


if __name__ == "__main__":
    # TODO: Load from yaml or initialize it using AutoGPT
    org = Organization("A cool AGI organization")
    org.create_agent(founder=True)  # Founder of te organization.
    org.run()  # Run te org
