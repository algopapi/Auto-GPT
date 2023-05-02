import asyncio
import glob
import importlib.resources
import os
import threading
from functools import wraps
from typing import Dict, List

import matplotlib.pyplot as plt
import networkx as nx
import yaml
from yaml.constructor import ConstructorError


def construct_python_tuple(constructor, node):
    return tuple(constructor.construct_sequence(node))

from colorama import Fore, Style

import permanent_storage
from autogpt.agent import Agent
from autogpt.config import Config
from autogpt.config.ai_config import AIConfig
from autogpt.config.config import Singleton
from autogpt.logs import logger
from autogpt.memory import get_memory


def update_yaml_after(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if not kwargs.get("skip_update_yaml", False):
            self.save()
        return result

    return wrapper


def update_and_visualize(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)
        await self.visualize_organization()
        return result

    return wrapper

cfg = Config()
# An organization of multiple agents.
class Organization(metaclass=Singleton):
    def __init__(self, name, initial_budget):
        self.name = name
       
        self.agents: Dict[int, Agent] = {}
        self.print_lock = threading.Lock()  # Create a lock for print statements
        self.initial_budget = initial_budget
        self.agent_budgets = {}
        self.agent_running_costs = {}
        self.pending_messages = {}
        self.agent_statuses = {}
        self.supervisor_to_staff: Dict[int, List[int]] = {}  # Maps supervisor ID to staff IDs
        self.agent_termination_events = {}

        self.file_path = f'{self.name}_organization.yaml'

        # Some locks
        self.hire_fire_lock = asyncio.Lock()
        self.yaml_lock = asyncio.Lock()


        self.save()


    async def visualize_organization(self):
        G = nx.DiGraph()
        # Add nodes and edges
        for supervisor_id, staff_ids in self.supervisor_to_staff.items():
            supervisor = self.agents.get(supervisor_id)
            if supervisor is not None:
                G.add_node(supervisor_id, label=supervisor.name)

                for staff_id in staff_ids:
                    staff_agent = self.agents.get(staff_id)
                    if staff_agent is not None:
                        G.add_node(staff_id, label=staff_agent.name)
                        G.add_edge(supervisor_id, staff_id)

        # Set node labels
        labels = {node: f"{data['label']} ({node})\nCost: {self.agent_running_costs[node]}\nBudget: {self.agent_budgets[node]}"
                  for node, data in G.nodes(data=True)}

        # Plot the graph
        def plot_graph():
            pos = nx.spring_layout(G)
            nx.draw(G, pos, with_labels=False, node_size=3000, node_color="skyblue")
            nx.draw_networkx_labels(G, pos, labels)
            plt.show()

        # Schedule the graph plotting on the default event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, plot_graph)


    @classmethod
    def load(cls, organization_name):
       
        """
            Function that loads the organization yaml file and loads in the organization data and all the agents
        """
        # Update the organization_folder to use importlib.resources.files
        organization_folder = (
            importlib.resources.files(permanent_storage) / f"organizations/{organization_name}"
        )

        org_file_path = organization_folder / f"{organization_name}_organization.yaml"
        print(" org file path",  org_file_path)


        # Load organization data from the YAML file
        with open(org_file_path, 'r') as org_file:
            yaml.SafeLoader.add_constructor('tag:yaml.org,2002:python/tuple', construct_python_tuple)
            org_data = yaml.safe_load(org_file)

        print("org_data", org_data)

        org = Organization(org_data['name'], org_data['initial_budget'])
        org.agent_budgets = org_data['agent_budgets']
        org.agent_running_costs = org_data['agent_running_costs']
        org.pending_messages = org_data['pending_messages']
        org.agent_statuses = org_data['agent_statuses']
        org.supervisor_to_staff = org_data['supervisor_to_staff']

       
        agent_files = glob.glob(str(organization_folder / "agents" / "*.yaml"))

        # Create all the agents
        for file_path in agent_files:
            print("file path", file_path)
            agent_config = AIConfig.load(file_path) # This should be the
            print("agent_config", agent_config)
            if agent_config is not None:
                agent_config.init_memory = False
                print(" adding  agent", agent_config)
                org.add_agent(agent_config)

       
        # Add staff to supervisor
        for supervisor_id, staff_ids in org.supervisor_to_staff.items():
            supervisor = org.agents.get(supervisor_id)
            if supervisor is not None:
                for staff_id in staff_ids:
                    staff_agent = org.agents.get(staff_id)
                    if staff_agent is not None:
                        supervisor.organization.add_staff(supervisor_id, staff_id, skip_update_yaml=True)

        print("loaded organization")

        return org
        

    async def save(self):
        async with self.yaml_lock:
            # Create a dictionary to store the relevant attributes
            data = {
                'name': self.name,
                'initial_budget': self.initial_budget,
                'agent_budgets': self.agent_budgets,
                'agent_running_costs': self.agent_running_costs,
                'pending_messages': self.pending_messages,
                'agent_statuses': self.agent_statuses,
                'supervisor_to_staff': self.supervisor_to_staff,
            }

            # Update the file path to include the organization_name
            org_directory = (
                importlib.resources.files(permanent_storage) / f"organizations/{self.name}"
            )
            self.file_path = str(org_directory / f"{self.name}_organization.yaml")

            # Ensure the directory exists
            if not os.path.exists(org_directory):
                os.makedirs(org_directory)

            # Write the data to the YAML file
            with open(self.file_path, 'w') as file:
                yaml.dump(data, file)


    def find_agent_by_id(self, agent_id):
        try:
            return self.agents[agent_id]
        except KeyError:
            return None


    async def start_agent_loop(self, agent):
        print(" STARTING AGENT LOOP")
        #await agent.start_interaction_loop()
        await agent.start_test_loop()


    async def start_all_agent_loops(self):
        # Create tasks for each agent loop

        tasks = [self.start_agent_loop(agent) for agent in self.agents.values()]
        await asyncio.gather(*tasks)


    async def start_all_agent_loops_2(self):
        # Create tasks for each agent loop
        tasks = []
        for agent in self.agents.values():
            termination_event = asyncio.Event()
            self.agent_termination_events[agent.ai_id] = termination_event
            tasks.append(self.start_agent_loop(agent, termination_event))
        await asyncio.gather(*tasks)


    async def start(self):
        await self.start_all_agent_loops_2()
    

    def print_sync(self, *args, **kwargs):
        """Synchronized print function that ensures ordered output"""
        with self.print_lock:
            print(*args, **kwargs)


    async def hire_staff(self, name, role, goals, budget, supervisor_name, supervisor_id):
        async with self.hire_fire_lock:
            new_employee = self.create_agent(
                name=name,
                role=role,
                goals=goals,
                budget=budget,
                founder=False,
            )
            new_employee_id = new_employee.ai_id  # Retrieve the ai_id of the new employee
            
            # Start the interection loop of the newly hired agent
           
            asyncio.ensure_future(self.start_agent_loop(new_employee))


            return self.add_staff(supervisor_id, new_employee_id)
    
    
    def create_agent(
        self,
        name,
        role,
        goals,
        budget,
        founder=False,
    ):
        agent_id = len(self.agents)
        agent_file = (
            importlib.resources.files(permanent_storage)
            / f"organizations/{self.name}/agents/{agent_id}_{name}.yaml"
        )
        print(" Agent file: ", agent_file)
        

        agent_cfg = AIConfig(
            ai_name=name,
            ai_id=agent_id,
            ai_role=role,
            ai_goals=goals,
            file_path=agent_file,
        )

        self.agent_budgets[agent_id] = budget
        return self.add_agent(agent_cfg)
    
    
    @update_yaml_after
    def add_staff(self, supervisor_id, new_employee_id, skip_update_yaml=False):

        if skip_update_yaml:
            return

        if supervisor_id not in self.supervisor_to_staff:
            self.supervisor_to_staff[supervisor_id] = []
        
        self.supervisor_to_staff[supervisor_id].append(new_employee_id)

        # Initialize the new agent's status 
        self.agent_statuses[new_employee_id] = f"agent is on its way on joining the company"

        return f"Successfully added employee with Agent_id: {new_employee_id} to supervisor with Agent_id: {supervisor_id}\n"


    @update_yaml_after
    def add_agent(self, agent_cfg):
        
        print("adding agent with ")
        print("agent_cfg ", agent_cfg)
        print("agent_id", agent_cfg.ai_id)
        print ("organization ", self.name)


        memory = get_memory(cfg=cfg, organization_name=self.name, agent_config=agent_cfg)
        new_agent = Agent(agent_cfg, self, memory)
        
        print("new_agent_id", new_agent.ai_id)
        self.agents[new_agent.ai_id] = new_agent

        print(f"\n {self.agents} \n")
        return new_agent



    @update_yaml_after
    def route_message(self, sender_id, reciever_id, message):
        logger.typewriter_log(
            f"ORG: Sender Id: {sender_id} \n ORG: Reciever Id: {reciever_id} \n ORG: Message: {message} \n"
        )
        
    
    @update_yaml_after
    async def message_staff(self, sender_id, receiver_id, message):
        try:
            sender_id = int(sender_id)
        except ValueError:
            return "You're likely entering the employee name as agent_id, please enter a valid integer agent_id"

        receiver = self.find_agent_by_id(receiver_id)

        if receiver:
            if receiver_id not in self.pending_messages:
                self.pending_messages[receiver_id] = []

            self.pending_messages[receiver_id].append((sender_id, message))
            return f"Successfully sent message to employee {receiver.ai_name}\n"
        else:
            return f"Failed to send message to employee with Agent_id: {receiver_id}\n"
       
       
    async def list_staff(self):
        employee_list = self.build_status_update()
        return employee_list


    @update_yaml_after
    async def fire_staff(self, agent_id):
        async with self.hire_fire_lock:
            # Check if the agent ID exists in the agents dictionary
            
            if agent_id in self.agents:

                # Set the termination event for the fired agent
                termination_event = self.agent_termination_events.get(agent_id)
                if termination_event:
                    termination_event.set()
                
                agent = self.agents[agent_id]
                agent_name = agent.ai_name

                # Check if the agent has employees
                if agent_id in self.supervisor_to_staff and self.supervisor_to_staff[agent_id]:
                    return f"Agent {agent_name} cannot be fired because they have employees. Instruct them to let go of their workforce so they can be fired.\n"

                # Remove the agent from the supervisor's staff list if applicable
                if not agent.founder:
                    supervisor_id = self.get_supervisor_id(agent_id)
                    # Check if supervisor_id is in supervisor_to_staff and remove the agent_id from the staff list
                    if supervisor_id in self.supervisor_to_staff and agent_id in self.supervisor_to_staff[supervisor_id]:
                        self.supervisor_to_staff[supervisor_id].remove(agent_id)

                        # Remove the supervisor's entry from the dictionary if they have no more staff
                        if not self.supervisor_to_staff[supervisor_id]:
                            del self.supervisor_to_staff[supervisor_id]

                # Remove pending messages, running costs, budgets, and statuses
                if agent_id in self.pending_messages:
                    del self.pending_messages[agent_id]
                if agent_id in self.agent_running_costs:
                    del self.agent_running_costs[agent_id]
                if agent_id in self.agent_budgets:
                    del self.agent_budgets[agent_id]
                if agent_id in self.agent_statuses:
                    del self.agent_statuses[agent_id]

                # Remove the agent from the organization
                await self.remove_agent(agent_id)

                return f"Successfully removed employee with name: {agent_name}\n"
            else:
                return f"Failed to remove employee with Agent_id: {agent_id}\n"
            
    @update_yaml_after
    async def remove_agent(self, agent_id):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.ai_config.remove()
            del self.agents[agent_id]
            return True
        else:
            return False

    
    async def message_supervisor(self, sender_id, message):
        """
        Auto routes a message from the staff member to the supervisor
        """
        # Look up the sender agent using sender_id
        sender = self.agents[sender_id]
        
        # Check if the sender ageWnt is the founder
        supervisor_id = self.get_supervisor_id(sender_id)
        
        if not sender.founder:
            if supervisor_id is not None:
                # Route the message from the sender to the supervisor
                self.route_message(sender_id, supervisor_id, message)
                return f"Successfully sent message to your supervisor\n"
            else: 
                return f"Could not find your supervisors id"
        else: 
            return f"You are the founder and therefore don't have a supervisor!\n"


    @update_yaml_after
    async def receive_message(self, agent_id):
        # Check if the agent ID exists in the pending_messages dictionary
        if agent_id in self.pending_messages:
            # Pop the first message from the agent's pending message list
            message_list = self.pending_messages[agent_id]
            if message_list:
                message = message_list.pop(0)
                return message
            else:
                return "You have no pending messages"  # No pending messages for the agent
        else:
            return None  # Agent ID not found in the pending_messages dictionary


    def get_pending_messages(self, agent_id):
        return self.pending_messages.get(agent_id, [])
    

    async def calculate_operating_cost(self, cost_per_step=100):
        total_running_cost = 0
        for agent_id, agent in self.agents.items():
            agent_running_cost = await self.calculate_operating_cost_of_agent(agent_id, cost_per_step)
            total_running_cost += agent_running_cost
        return total_running_cost


    @update_yaml_after
    async def calculate_operating_cost_of_agent(self, agent_id, cost_per_step = 100):
        # Base cost for the agent
        agent_running_cost = cost_per_step
        # Add the operating cost of each employee under this agent
        for employee_id in self.supervisor_to_staff.get(agent_id, []):
            agent_running_cost += await self.calculate_operating_cost_of_agent(employee_id, cost_per_step)
        
        # Save the calculated running cost in the agent_running_costs dictionary
        self.agent_running_costs[agent_id] = agent_running_cost
        
        return agent_running_cost

    
    def has_staff(self, agent_id):
        return bool(self.supervisor_to_staff.get(agent_id, []))


    def get_supervisor_id(self, agent_id):
        for supervisor, staff in self.supervisor_to_staff.items():
            if agent_id in staff:
                return supervisor
        return None


    async def get_staff(self, agent_id):
        staff_ids = self.supervisor_to_staff.get(agent_id, [])
        staff_list = [self.agents[staff_id] for staff_id in staff_ids]
        return staff_list
    

    async def build_status_update(self, agent_id):
        staff_info = f"Your Staff Status:\n\n"
        if not self.has_staff(agent_id):
            staff_info += f"Agent {agent_id} currently has no staff in service\n"
        else:
            staff_info += self.get_employee_hierarchy(agent_id, 0)
        return staff_info


    def get_employee_hierarchy(self, supervisor_id, level): 
        hierarchy = ""
        indent = "  " * level
        if supervisor_id is None:
            agents = self.agents.values()
        else:
            agents = [self.agents[employee_id] for employee_id in self.supervisor_to_staff.get(supervisor_id, [])]
        for agent in agents:
            hierarchy += (
                f"{indent}Agent_Id:{agent.ai_id}. Agent_Name: {agent.ai_name}, Supervisor: {self.agents[supervisor_id].ai_name if supervisor_id is not None else 'None'}\n"
                f"{indent}Role: {agent.role}, Status: {self.agent_statuses[agent.ai_id]}, Operating Cost: {self.agent_running_costs[agent.ai_id]}, Budget: {self.agent_budgets[agent.ai_id]}\n"
            )
            hierarchy += self.get_employee_hierarchy(agent.ai_id, level + 1)

        return hierarchy


    @update_yaml_after
    async def update_agent_status(self, agent_id, status):
        self.agent_statuses[agent_id] = status
    

    def get_agent_status(self, agent_id):
        return self.agent_statuses.get(agent_id, "Unknown")
    

    @update_yaml_after
    async def update_agent_budget(self, agent_id, running_cost):
        self.agent_budgets[agent_id] -= running_cost
