import glob
import importlib.resources
import os
import threading
from typing import Dict, List

from colorama import Fore, Style

import permanent_storage
from auto_gpt.logger import logger
from auto_gpt.utils.print_utils import print_to_console

from .agent import Agent, AgentConfig


# An organization of multiple agent.
class Organization:
    def __init__(self, name):
        self.name = name
        self.agents: Dict[int, Agent] = {}
        self.print_lock = threading.Lock()  # Create a lock for print statements

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
                agent_config.init_memory = False
                org.add_agent(agent_config)

        # Add staff to supervisor
        for _, agent in org.agents.items():
            if not agent.cfg.founder:
                supervisor = org.agents[agent.cfg.supervisor_id]
                if supervisor is not None:
                    supervisor.add_staff(agent)
        return org
    
    def find_agent_by_id(self, agent_id):
        try:
            return self.agents[agent_id]
        except KeyError:
            return None

    def run(self):
            # Create and start a new thread for each agent
            threads = []
            for agent in self.agents.values():
                t = threading.Thread(target=self.run_agent, args=(agent,))
                t.start()
                threads.append(t)

            # Wait for all threads to finish
            for t in threads:
                t.join()

    def run_agent(self, agent):
        with self.print_lock:
            # print(
            #     Fore.GREEN
            #     + f"\n ---------------- Running agent {agent.cfg.name} -----------------\n"
            #     + Style.RESET_ALL,
            #     end="",
            # )

            logger.typewriter_log(
                f"\n ---------------- Running agent {agent.cfg.name} -----------------\n"
            )
        agent.step()

    def print_sync(self, *args, **kwargs):
        """Synchronized print function that ensures ordered output"""
        with self.print_lock:
            print(*args, **kwargs)



    def create_agent(
        self,
        name,
        task,
        goals,
        supervisor_name=None,
        supervisor_id=None,
        founder=False,
    ):
        agent_id = len(self.agents)
        organization_file = (
            importlib.resources.files(permanent_storage)
            / f"organizations/{self.name}/{agent_id}_{name}.yaml"
        )
        agent_cfg = AgentConfig(
            file_path=organization_file,
            name=name,
            agent_id=agent_id,
            task=task,
            goals=goals,
            supervisor_name=supervisor_name,
            supervisor_id=supervisor_id,
            founder=founder,
        )
        return self.add_agent(agent_cfg)

    def add_agent(self, agent_cfg):
        new_agent = Agent(organization=self, agent_config=agent_cfg)
        self.agents[new_agent.agent_id] = new_agent
        return new_agent

    def remove_agent(self, agent_id):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.cfg.remove()
            del self.agents[agent_id]
            return True
        else:
            return False

    def route_message(self, sender, reciever, message):

        logger.typewriter_log(
            f"ORG: Sender: {sender.agent_name} \n ORG: Reciever: {reciever.agent_name} \n ORG: Message: {message} \n"
        )

        reciever.recieve_message(sender, message)


if __name__ == "__main__":
    # TODO: Load from yaml or initialize it using AutoGPT
    org = Organization("A cool AGI organization")
    org.create_agent(name="founder", task="Setup an organization", goals="1. hire 1 arbitrary staff member\n 2. say hello \n 3. fire the staff member", founder=True)  # Founder of te organization.
    org.run()  # Run te org
