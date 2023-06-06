import asyncio
import functools
import glob
import os
import signal
from functools import wraps
from typing import Dict, List

import aiofiles
import matplotlib.pyplot as plt
import networkx as nx
import yaml
from colorama import Fore, Style
from yaml.constructor import ConstructorError

from autogpt.agent import Agent
from autogpt.commands.command import CommandRegistry
from autogpt.config import Config
from autogpt.config.ai_config import AIConfig
from autogpt.config.config import Singleton
from autogpt.logs import logger
from autogpt.memory.vector import get_memory

COMMAND_CATEGORIES = [
    "autogpt.commands.analyze_code",
    "autogpt.commands.audio_text",
    "autogpt.commands.execute_code",
    "autogpt.commands.file_operations",
    "autogpt.commands.git_operations",
    "autogpt.commands.google_search",
    "autogpt.commands.image_gen",
    "autogpt.commands.improve_code",
    "autogpt.commands.web_selenium",
    "autogpt.commands.write_tests",
    "autogpt.app",
    "autogpt.commands.task_statuses",
]

class DebuggableQueue(asyncio.Queue):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def print_contents(self):
        # Access the internal queue (_queue) and print the action and agent attributes
        for event in list(self._queue):
            print(f"Event action: {event.action}, Agent: {event.agent}")

    async def filter_queue(self, condition):
        """
        Filters the queue based on the given condition.
        
        :param condition: A callable that takes an event and returns a boolean value. If the condition returns True, the event will be kept in the queue.
        """
        temp_queue = []
        while not self.empty():
            event = self.get_nowait()
            if condition(event):
                temp_queue.append(event)
        for event in temp_queue:
            await self.put(event)


def construct_python_tuple(constructor, node):
    return tuple(constructor.construct_sequence(node))



def update_and_visualize(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)
        await self.visualize_organization()
        return result
    return wrapper



async def update_yaml_after(func):
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        result = await func(self, *args, **kwargs)
        if not kwargs.get("skip_update_yaml", False):
            await self.a_save()
        return result
    return wrapper


async def async_update_yaml(obj, yaml_path):
    
    # Create a dictionary to represent the organization data
    org_data = {
        'name': obj.name,
        'initial_budget': obj.initial_budget,
        'agent_budgets': obj.agent_budgets,
        'agent_running_costs': obj.agent_running_costs,
        'pending_messages': obj.pending_messages,
        'agent_statuses': obj.agent_statuses,
        'supervisor_to_staff': obj.supervisor_to_staff,
        'agent_termination_events': obj.agent_termination_events,
    }

    async with aiofiles.open(yaml_path, mode='w') as outfile:
        await outfile.write(yaml.dump(org_data))



def update_yaml_after_async(func):
    async def wrapper(*args, **kwargs):
        print("Updating YAML file after function call.")
        obj = args[0]
        async with obj.action_lock:
            res = await func(*args, **kwargs)
            file_path = obj.org_yaml_path

            async with obj.file_lock:  # Use the file lock here
                await async_update_yaml(obj, file_path)
        print(" YAML file updated.")
        return res
    return wrapper


cfg = Config()
# An organization of multiple agents.
class Organization(metaclass=Singleton):
    def __init__(self, name, initial_budget):
        self.name = name
        self.agents: Dict[int, Agent] = {}
        self.running_agents = []
        self.initial_budget = initial_budget
        self.free_agent_ids: List[int] = []
        self.agent_budgets = {}
        self.agent_running_costs = {}
        self.pending_messages = {}
        self.agent_statuses = {}
        self.supervisor_to_staff: Dict[int, List[int]] = {}  # Maps supervisor ID to staff IDs
        self.agent_termination_events = {}

        # File paths
        self.org_dir_path = f"{cfg.workspace_path}/{self.name}"
        self.org_yaml_path = self.org_dir_path + "/" + f"{self.name}_organization.yaml"
       
        print("org workspace", self.org_dir_path)

        # Organization event queue
        self.event_queue = DebuggableQueue()
        self.event_results = {}

        # Handles termination
        self.termination_event = asyncio.Event()

        # Some locks
        #self.org_lock = asyncio.Lock()  # Create a lock for the organization
        self.action_lock = asyncio.Lock()
        self.file_lock = asyncio.Lock()
        self.org_lock = asyncio.Lock()
        

    async def register_agent(self, agent):
        self.running_agents.append(agent)


    async def notify_termination(self, agent):
        self.running_agents.remove(agent)


    async def process_events(self):
        iteration_count = 0
        while not self.termination_event.is_set():
            try:
                # Wait for an event to be available in the queue or for the timeout to be reached
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # If the timeout was reached, continue to the next iteration of the loop
                continue

            if event.agent.ai_id in self.agents:
                await event.process()  # Call the process method for each event
            else:
                print(f"Discarded event from terminated agent {event.agent.ai_id}.")
            self.event_queue.task_done()

            # Print the contents of the queue every other iteration
            iteration_count += 1
            if iteration_count % 50 == 0:
                print("Contents of the event queue:")
                self.event_queue.print_contents()
            print('\n processing event \n')
        print("\nTermination event set. Exited process_events loop.\n")
        


    async def get_event_result(self, event_id):
        while event_id not in self.event_results:
            await asyncio.sleep(0.1)
        result = self.event_results[event_id]
        del self.event_results[event_id]
        return result


    def convert_string_to_list(self, comma_separated_string):
        return comma_separated_string.split(',')


    async def perform_action(self, event_type, agent_id, *args, **kwargs):
        # Determine the action to perform based on the event_type
      
        async with self.org_lock:
            # Do a final check so that fired agents can sneak in an action
            print(f"\n Agent {agent_id} is about to perform an action {event_type}.")
            
            if agent_id in self.agents and self.agents[agent_id].terminated:
                return f"Agent {self.agents[agent_id].ai_name} is terminated and cannot perform actions."

            if event_type == 'get_staff':
                return self.get_staff(agent_id)

            elif event_type == 'hire_staff':
                # Perform the 'hire_staff' action and return the result
                print(f"free agent ids:", self.free_agent_ids)
                name, role, goals, budget, supervisor_name, supervisor_id = args
                goals_list = self.convert_string_to_list(goals)
                print("goals list", goals_list)
                res = await self.hire_staff(name, role, goals_list, budget, supervisor_name, supervisor_id)
                print(f"Agent {name} response to hiring staff: {res}")
                return res

            elif event_type == 'fire_staff':
                # Perform the 'fire_staff' action and return the result
                print(f"free agent ids:", self.free_agent_ids)
                ai_id = args[0]
                print(f"the agent that is going to be fired is: {ai_id}")
                res = await self.fire_staff(ai_id)
                print(f"Agent {ai_id} response to firing staff: {res}")
                return res

            elif event_type == 'message_staff':
                # Perform the 'message_staff' action and return the result
                sender_id, receiver_id, message = args
                print("sender_id", sender_id)
                print("receiver_id", receiver_id)
                print("message", message)
                return await self.message_staff(sender_id, receiver_id, message)

            elif event_type == 'message_supervisor':
                # Perform the 'message_supervisor' action and return the result
                sender_id, message = args
                return await self.message_supervisor(sender_id, message)
        
            elif event_type == 'receive_message':
                agent_id = args[0]
                return await self.receive_message(agent_id)

            elif event_type == 'calculate_operating_cost_of_agent':
                # Perform the 'calculate_operating_cost_of_agent' action and return the result
                ai_id = args[0]
                res =  await self.calculate_operating_cost_of_agent(ai_id)
                print(f" Agent {ai_id} response to calculating operating cost: {res}")
                return res
            
            elif event_type == 'update_agent_running_cost':
                # Perform the 'calculate_operating_cost_of_agent' action and return the result
                ai_id, running_cost= args
                res = await self.update_agent_running_cost(ai_id, running_cost)
                print(f" Agent {ai_id} response to updating running cost: {res}")
                return res
            
            elif event_type == 'update_agent_budget':
                ai_id, running_cost = args
                res = await self.update_agent_budget(ai_id, running_cost)
                print(f" Agent {ai_id} response to updating budget: {res}")
                return res

            elif event_type == 'update_agent_status':
                ai_id, status = args
                res = await self.update_agent_status(ai_id, status)
                print(f" Agent {ai_id} response to updating status: {res}")
                return res
            
            elif event_type == 'build_status_update':
                ai_id = args[0]
                res = await self.build_status_update(ai_id)
                return res

            else:
                # Raise an error if the event_type is not recognized
                raise ValueError(f"Unknown event type: {event_type}")
            
    
    @classmethod
    def create(cls, name, initial_budget):
        org = cls(name, initial_budget)
        org.save()
        return org


    async def start_agent_loop(self, agent):
        # Register agent in running agents (handy for cleanup)
        await self.register_agent(agent)
        # await agent.start_interaction_loop(self.termination_event)
        await agent.start_test_loop(self.termination_event)

    
    async def start_event_processing_loop(self):
        await self.process_events()

    
    async def start_all_agent_loops(self):
        # Create tasks for each agent loop
        tasks = [self.start_agent_loop(agent) for agent in self.agents.values()]
        
        # Create a seperate task for the event processing loop
        tasks.append(self.start_event_processing_loop())

        # Gather all tasks and run them concurrently
        await asyncio.gather(*tasks)

    
    async def start(self):
        await self.start_all_agent_loops()
    

    @update_yaml_after_async
    async def hire_staff(self, name, role, goals, budget, supervisor_name, supervisor_id):
        try:
            # Validate and convert budget to integer
            budget = int(budget)
        except ValueError:
            raise ValueError(f"Budget value '{budget}' is not a valid integer.")
        
        new_employee = await self.a_create_agent(
            name=name,
            role=role,
            goals=goals,
            founder=False,
        )
        new_employee_id = new_employee.ai_id  # Retrieve the ai_id of the new employee
        res = await self.add_staff(supervisor_id, new_employee_id, budget)
        # Start the interection loop of the newly hired agent
        asyncio.create_task(self.start_agent_loop(new_employee))
        return res
    

    @update_yaml_after_async
    async def fire_staff(self, agent_id):
        # Check if the agent ID exists in the agents dictionary
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent_name = agent.ai_name

            # Check if the agent has employees
            if agent_id in self.supervisor_to_staff and self.supervisor_to_staff[agent_id]:
                return f"Agent {agent_name} cannot be fired because they have employees. Instruct them to let go of their workforce so they can be fired.\n"
            
            # Terminate the agent loop
            agent.terminated = True
            
            # Remove the agent from the supervisor's staff list if applicable
            if not agent.founder:
                supervisor_id = await self.get_supervisor_id(agent_id)
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

            # Remove agent events from the event queue
            await self.event_queue.filter_queue(lambda event: event.agent.ai_id != agent_id)
            self.free_agent_ids.append(agent_id)
          
            # Remove the agent from the organization
            await self.remove_agent(agent_id)
            return f"Successfully removed employee with name: {agent_name}\n"
        else:
            return f"Failed to remove employee with Agent_id: {agent_id}\n"
            


    async def add_staff(self, supervisor_id, new_employee_id, budget, skip_update_yaml=False):
        if skip_update_yaml:
            return

        if supervisor_id not in self.supervisor_to_staff:
            self.supervisor_to_staff[supervisor_id] = []
        
        # Set the supervisor
        self.supervisor_to_staff[supervisor_id].append(new_employee_id)

        # Initialize the new agent's status 
        self.agent_statuses[new_employee_id] = f"agent is on its way on joining the company"

        # Initialize agent budget
        self.agent_budgets[new_employee_id] = budget

        # Initialize the agent running costs
        self.agent_running_costs[new_employee_id] = 100
        
        return f"Successfully added employee with Agent_id: {new_employee_id} to supervisor with Agent_id: {supervisor_id}\n"
    

    async def a_add_agent(self, agent_cfg):
        agent_mem_path = f"{self.org_dir_path}/agents/{agent_cfg.ai_id}_{agent_cfg.ai_name}_workspace/agent_memory.json"
        memory = get_memory(cfg=cfg, agent_mem_path=agent_mem_path)
                # Create the commands that should be passed to the staffmember
        command_registry = CommandRegistry()

        enabled_command_catergories = [
            x for x in COMMAND_CATEGORIES if x not in cfg.disabled_command_categories
        ]

        for command_catergory in enabled_command_catergories:
            command_registry.import_commands(command_catergory)

        new_agent = Agent(
            memory = memory,
            next_action_count=0,
            command_registry="",
            triggering_prompt="",
            config = agent_cfg,
            system_prompt = "",
            workspace_directory="",
            organization=self,
        )

        self.agents[new_agent.ai_id] = new_agent
        return new_agent
    

    def add_agent(self, agent_cfg):
        agent_mem_path = f"{self.org_dir_path}/agents/{agent_cfg.ai_id}_{agent_cfg.ai_name}_workspace/agent_memory.json"
        memory = get_memory(cfg=cfg, agent_mem_path=agent_mem_path)
                # Create the commands that should be passed to the staffmember
        command_registry = CommandRegistry()

        enabled_command_catergories = [
            x for x in COMMAND_CATEGORIES if x not in cfg.disabled_command_categories
        ]

        for command_catergory in enabled_command_catergories:
            command_registry.import_commands(command_catergory)

        new_agent = Agent(
            memory = memory,
            next_action_count=0,
            command_registry="",
            triggering_prompt="",
            config = agent_cfg,
            system_prompt = "",
            workspace_directory="",
            organization=self,
        )

        self.agents[new_agent.ai_id] = new_agent
        return new_agent


    async def a_create_agent(
        self,
        name,
        role,
        goals,
        initial_budget = 0,
        founder=False,
    ):
        if self.free_agent_ids:
            # Allocate from freed Ids if available
            agent_id = self.free_agent_ids.pop(0)
            print(" Agent id Popped = ", agent_id)
        else:
            agent_id = len(self.agents)
            print(" agent id Assigned = ", agent_id)

        agent_workspace_directory = f"{self.org_dir_path}/agents/{agent_id}_{name}_workspace"
        agent_cfg = AIConfig(
            ai_name=name,
            ai_id=agent_id,
            ai_role=role,
            ai_goals=goals,
            founder=founder,
            file_path=agent_workspace_directory,
        )

        # If it is the founder we set the budget here
        if founder:
            self.agent_budgets[agent_id] = initial_budget

        return await self.a_add_agent(agent_cfg)
    
    def create_agent(
        self,
        name,
        role,
        goals,
        initial_budget = 0,
        founder=False,
    ):
        if self.free_agent_ids:
            # Allocate from freed Ids if available
            agent_id = self.free_agent_ids.pop(0)
            print(" Agent id Popped = ", agent_id)
        else:
            agent_id = len(self.agents)
            print(" agent id Assigned = ", agent_id)

        agent_workspace_directory = f"{self.org_dir_path}/agents/{agent_id}_{name}_workspace"

        agent_cfg = AIConfig(
            ai_name=name,
            ai_id=agent_id,
            ai_role=role,
            ai_goals=goals,
            founder=founder,
            file_path=agent_workspace_directory,
        )

        # If it is the founder we set the budget here
        if founder:
            self.agent_budgets[agent_id] = initial_budget

        return self.add_agent(agent_cfg)


    async def remove_agent(self, agent_id):
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.ai_config.remove()
            del self.agents[agent_id]
            return True
        else:
            return False


    async def list_staff(self, agent_id):
        employee_status = self.build_status_update(agent_id)
        return employee_status


    @update_yaml_after_async
    async def message_staff(self, sender_id, receiver_id, message):
        try:
            receiver_id = int(receiver_id)
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
    

    @update_yaml_after_async
    async def message_supervisor(self, sender_id, message):
        """
        Auto routes a message from the staff member to the supervisor
        """
      
        # Look up the sender agent using sender_id
        sender = self.agents[sender_id]
        
        # Check if the sender ageWnt is the founder
        supervisor_id =  await self.get_supervisor_id(sender_id)
        
        if not sender.founder:
            if supervisor_id is not None:
                if supervisor_id not in self.pending_messages:
                    self.pending_messages[supervisor_id] = []

                self.pending_messages[supervisor_id].append((sender_id, message))
                return f"Successfully sent message to your supervisor\n"
            else: 
                return f"Could not find your supervisors id"
        else: 
            return f"You are the founder and therefore don't have a supervisor!\n"
            

    @update_yaml_after_async
    async def receive_message(self, agent_id):
        # Check if the agent ID exists in the pending_messages dictionary
        if agent_id in self.pending_messages:
            # Pop the first message from the agent's pending message list
            message_list = self.pending_messages[agent_id]
            if message_list:
                message = message_list.pop(0)
                send = f"agent id: {message[0]} sent you the following message: {message[1]}"
                return send
            else:
                return "You have no pending messages"  # No pending messages for the agent
        else:
            return "You have no pending messages"  # Agent ID not found in the pending_messages dictionary


    @update_yaml_after_async
    async def update_agent_running_cost(self, agent_id, agent_running_cost):
        self.agent_running_costs[agent_id] = agent_running_cost
        # The YAML file will be updated after this method is completed


    @update_yaml_after_async
    async def calculate_operating_cost_of_agent(self, agent_id, cost_per_step=100):
        return await self._recursive_calculate_operating_cost(agent_id, cost_per_step=100)


    async def _recursive_calculate_operating_cost(self, agent_id, cost_per_step=100):
        # Base cost for the agent
        agent_running_cost = cost_per_step
        # Add the operating cost of each employee under this agent
        for employee_id in self.supervisor_to_staff.get(agent_id, []):
            agent_running_cost += await self._recursive_calculate_operating_cost(employee_id, cost_per_step)
        return agent_running_cost


    @update_yaml_after_async
    async def update_agent_status(self, agent_id, status):
        self.agent_statuses[agent_id] = status
        return f"Successfully updated employee with Agent_id: {agent_id} status to {status}\n"


    @update_yaml_after_async
    async def update_agent_budget(self, agent_id, running_cost):
        self.agent_budgets[agent_id] -= running_cost


    async def get_agent_status(self, agent_id):
        return self.agent_statuses.get(agent_id, "Unknown")


    async def build_status_update(self, agent_id):
        staff_info = f"Your Staff Status:\n"
        
        if not await self.has_staff(agent_id):
            staff_info += f"Agent {agent_id} currently has no staff in service\n"
        else:
            staff_info += self.get_employee_hierarchy(agent_id, 0)
    
        # Build organization info context for agent
        running_costs = await self.calculate_operating_cost_of_agent(agent_id)
        budget = self.agent_budgets[agent_id]
        runaway_time = self.agent_budgets[agent_id] / running_costs
        staff_info += f"\n\n Your current budget is ${budget}\n"
        staff_info += f"Your current running costs are ${running_costs} per step\n"
        staff_info += f"With your current running costs you will run out in {runaway_time} steps.\n"
        staff_info += f"A simple task will typically take 15 steps."
        return staff_info

        
    def get_pending_messages(self, agent_id):
        return self.pending_messages.get(agent_id, [])
    

    async def has_staff(self, agent_id):
        return bool(self.supervisor_to_staff.get(agent_id, []))

    # Asynchornous function that returns supervisode ID.
    async def get_supervisor_id(self, agent_id):
        for supervisor, staff in self.supervisor_to_staff.items():
            if agent_id in staff:
                return supervisor
        return None
    
    def _get_supervisor_id(self, agent_id):
        for supervisor, staff in self.supervisor_to_staff.items():
            if agent_id in staff:
                return supervisor
        return None
        
    # Asynchronous method to get the supervisor's id and name
    def get_supervisor_info(self, agent_id: int):
        # Get the supervisor ID
        supervisor_id = self._get_supervisor_id(agent_id)
        # If there is a supervisor, return their ID and name
        if supervisor_id is not None:
            supervisor = self.agents.get(supervisor_id)
            if supervisor is not None:
                return supervisor_id, supervisor.ai_name
        # If there is no supervisor or the supervisor is not in the agents dictionary, return None
        print("cannot find supervisor for agent id ", agent_id)
        return None, None

    async def get_staff(self, agent_id):
        staff_ids = self.supervisor_to_staff.get(agent_id, [])
        staff_list = [self.agents[staff_id] for staff_id in staff_ids]
        return staff_list


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
    

    def find_agent_by_id(self, agent_id):
        try:
            return self.agents[agent_id]
        except KeyError:
            return None


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
    async def a_load(cls, organization_name):
        """
            Function that loads the organization yaml file and loads in the organization data and all the agents
        """
        # Update the organization_folder to use importlib.resources.files
        # organization_folder = (
        #     importlib.resources.files(permanent_storage)/f"organizations/{organization_name}"
        # ) 

        print("workspace path", cfg.workspace_path)
        organization_directory = os.path.join(cfg.workspace_path, organization_name)
        org_file_path = f"{organization_directory}/{organization_name}_organization.yaml"
        print("org file path",  org_file_path)

        # Load organization data from the YAML file
        with open(org_file_path, 'r') as org_file:
            yaml.SafeLoader.add_constructor('tag:yaml.org,2002:python/tuple', construct_python_tuple)
            org_data = yaml.safe_load(org_file)


        org = Organization(org_data['name'], org_data['initial_budget'])
        org.agent_budgets = org_data['agent_budgets']
        org.agent_running_costs = org_data['agent_running_costs']
        org.pending_messages = org_data['pending_messages']
        org.agent_statuses = org_data['agent_statuses']
        org.supervisor_to_staff = org_data['supervisor_to_staff']

       
        agent_directories = glob.glob(os.path.join(organization_directory, "agents", "*"))

        # Create all the agents
        for agent_dir in agent_directories:
            # print("file path", file_path)
            yaml_path = os.path.join(agent_dir, f"agent.yaml")

            agent_config = AIConfig.load(yaml_path) # This should be the
            # print("agent_config", agent_config)
            if agent_config is not None:
                agent_config.init_memory = False
                #print(" adding  agent", agent_config)
                org.add_agent(agent_config)

       
        # Add staff to supervisor
        for supervisor_id, staff_ids in org.supervisor_to_staff.items():
            supervisor = org.agents.get(supervisor_id)
            if supervisor is not None:
                for staff_id in staff_ids:
                    staff_agent = org.agents.get(staff_id)
                    if staff_agent is not None:
                        staff_budget = org.agent_budgets.get(staff_id)
                        supervisor.organization.add_staff(supervisor_id, staff_id, staff_budget, skip_update_yaml=True)

        return org
    
    @classmethod
    def load(cls, organization_name):
        """
            Function that loads the organization yaml file and loads in the organization data and all the agents
        """
        # Update the organization_folder to use importlib.resources.files
        # organization_folder = (
        #     importlib.resources.files(permanent_storage)/f"organizations/{organization_name}"
        # ) 

        print("workspace path", cfg.workspace_path)
        organization_directory = os.path.join(cfg.workspace_path, organization_name)
        org_file_path = f"{organization_directory}/{organization_name}_organization.yaml"
        print("org file path",  org_file_path)

        # Load organization data from the YAML file
        with open(org_file_path, 'r') as org_file:
            yaml.SafeLoader.add_constructor('tag:yaml.org,2002:python/tuple', construct_python_tuple)
            org_data = yaml.safe_load(org_file)


        org = Organization(org_data['name'], org_data['initial_budget'])
        org.agent_budgets = org_data['agent_budgets']
        org.agent_running_costs = org_data['agent_running_costs']
        org.pending_messages = org_data['pending_messages']
        org.agent_statuses = org_data['agent_statuses']
        org.supervisor_to_staff = org_data['supervisor_to_staff']

       
        agent_directories = glob.glob(os.path.join(organization_directory, "agents", "*"))

        # Create all the agents
        for agent_dir in agent_directories:
            # print("file path", file_path)
            yaml_path = os.path.join(agent_dir, f"agent.yaml")

            agent_config = AIConfig.load(yaml_path)
            # print("agent_config", agent_config)
            if agent_config is not None:
                agent_config.init_memory = False
                #print(" adding  agent", agent_config)
                org.add_agent(agent_config)

       
        # Add staff to supervisor
        for supervisor_id, staff_ids in org.supervisor_to_staff.items():
            supervisor = org.agents.get(supervisor_id)
            if supervisor is not None:
                for staff_id in staff_ids:
                    staff_agent = org.agents.get(staff_id)
                    if staff_agent is not None:
                        staff_budget = org.agent_budgets.get(staff_id)
                        supervisor.organization.add_staff(supervisor_id, staff_id, staff_budget, skip_update_yaml=True)

        return org
        

    async def a_save(self):
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

        print("saving organization at " , self.org_yaml_path)
        # Ensure the directory exists
        if not os.path.exists(self.org_dir_path):
            os.makedirs(self.org_dir_path)

        # Write the data to the YAML file
        with open(self.org_yaml_path, 'w') as file:
            yaml.dump(data, file)


    def save(self):
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

        print("saving organization at " , self.org_yaml_path)
        # Ensure the directory exists
        if not os.path.exists(self.org_dir_path):
            os.makedirs(self.org_dir_path)

        # Write the data to the YAML file
        with open(self.org_yaml_path, 'w') as file:
            yaml.dump(data, file)


    async def shutdown(self):
            # Signal all agents to stop generating new events
            for agent in self.agents.values():
                agent.terminated = True
            print("Signaled all agents to stop generating new events.")

            # Wait until all agents have succesfully terminated 
            while len(self.running_agents) > 0:
               
                await asyncio.sleep(1)

            print("All agents have terminated")


            # Now process remaining events
            while not self.event_queue.empty():  # check if there are still pending events
                print("processing remaining events")
                event = await self.event_queue.get()  # fetch an event from the queue
                await event.process()

            print("all remaining events have been processed")
         
            # Now it is safe to stop the event processing loop
            print("setting termination event")
            self.termination_event.set()
            print("[SHUTDOWN FINISHED] Stopped the event processing loop.")

    