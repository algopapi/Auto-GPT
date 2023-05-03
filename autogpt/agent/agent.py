import asyncio
import random
import string
import uuid

from colorama import Fore, Style

from autogpt.app import execute_command, get_command
from autogpt.chat import chat_with_ai, create_chat_message
from autogpt.config import Config
from autogpt.json_fixes.master_json_fix_method import fix_json_using_multiple_techniques
from autogpt.json_validation.validate_json import validate_json
from autogpt.logs import logger, print_assistant_thoughts
from autogpt.organization.org_events import Event
from autogpt.prompt import construct_prompt
from autogpt.speech import say_text
from autogpt.spinner import Spinner
from autogpt.utils import clean_input


class Agent:
    """Agent class for interacting with Auto-GPT.

    Attributes:
        ai_name: The name of the agent.
        memory: The memory object to use.
        full_message_history: The full message history.
        next_action_count: The number of actions to execute.
        system_prompt: The system prompt is the initial prompt that defines everything the AI needs to know to achieve its task successfully.
        Currently, the dynamic and customizable information in the system prompt are ai_name, description and goals.

        triggering_prompt: The last sentence the AI will see before answering. For Auto-GPT, this prompt is:
            Determine which next command to use, and respond using the format specified above:
            The triggering prompt is not part of the system prompt because between the system prompt and the triggering
            prompt we have contextual information that can distract the AI and make it forget that its goal is to find the next task to achieve.
            SYSTEM PROMPT
            CONTEXTUAL INFORMATION (memory, previous conversations, anything relevant)
            TRIGGERING PROMPT

        The triggering prompt reminds the AI about its short term meta task (defining the next task)
    """

    def __init__(
        self,
        ai_config,
        organization,
        memory,
        next_action_count=0
    ):  
        self.ai_config = ai_config
        self.ai_name = ai_config.ai_name
        self.ai_id = ai_config.ai_id
        self.role = ai_config.ai_role
        self.goals = ai_config.ai_goals

        self.terminated = ai_config.terminated
        self.loop_count = ai_config.loop_count
        self.founder = ai_config.founder

        self.respone_queue = asyncio.Queue()
        self.organization = organization
        self.memory = memory
        
        # We might want to define those here
        self.system_prompt = ai_config.construct_full_prompt()
        self.triggering_prompt = (
             "Determine which next command to use, and respond using the"
             " format specified above:"
         )
        
        self.next_action_count = next_action_count
        # You might want to save this in this case
        self.full_message_history = []

    async def update_agent_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.ai_config, key):
                setattr(self.ai_config, key, value)
            else:
                print(f"Unknown attribute '{key}' in AgentConfig.")
        self.ai_config.save()  # Save the updated configuration to the YAML file
        

    async def start_interaction_loop(self):
        print(f"\nstarting interaction loop of agent: {self.ai_name}\n")
        # Interaction Loop
        cfg = Config()
        loop_count = 0
        command_name = None
        arguments = None
        user_input = ""

        while True:
            message = self.organization.receive_message(self.ai_id)
            staff_update = self.organization.build_status_update(self.ai_id)
            print(f"Incoming message: {self.ai_name}:, \n{message}\n" )
            print(f"stafff update of agent: {self.ai_name}:, \n{staff_update}\n" )
            print(f"\n Running interaction loop {loop_count} of agent: {self.ai_name}\n")
            # Discontinue if continuous limit is reached
            loop_count += 1
            if (
                cfg.continuous_mode
                and cfg.continuous_limit > 0
                and loop_count > cfg.continuous_limit
            ):
                logger.typewriter_log(
                    "Continuous Limit Reached: ", Fore.YELLOW, f"{cfg.continuous_limit}"
                )
                break

            # Send message to AI, get response
            # with Spinner("Thinking... "):
            assistant_reply = await chat_with_ai(
                self.system_prompt,
                self.triggering_prompt,
                self.full_message_history,
                self.memory,
                cfg.fast_token_limit,
                self.ai_id
            )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument
           
            assistant_reply_json = await fix_json_using_multiple_techniques(assistant_reply)

            # Print Assistant thoughts
            if assistant_reply_json != {}:
                validate_json(assistant_reply_json, 'llm_response_format_1')
                # Get command name and arguments
                try:
                    print_assistant_thoughts(self.ai_name, assistant_reply_json)
                    command_name, arguments = get_command(assistant_reply_json)
                    # command_name, arguments = assistant_reply_json_valid["command"]["name"], assistant_reply_json_valid["command"]["args"]
                    if cfg.speak_mode:
                        say_text(f"I want to execute {command_name}")
                except Exception as e:
                    logger.error("Error: \n", str(e))

            if 1 == 0:
                ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
                # Get key press: Prompt the user to press enter to continue or escape
                # to exit
                logger.typewriter_log(
                    "NEXT ACTION: ",
                    Fore.CYAN,
                    f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
                    f"ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                )
                print(
                    "Enter 'y' to authorise command, 'y -N' to run N continuous "
                    "commands, 'n' to exit program, or enter feedback for "
                    f"{self.ai_name}...",
                    flush=True,
                )
                while True:
                    console_input = clean_input(
                        Fore.MAGENTA + "Input:" + Style.RESET_ALL
                    )
                    if console_input.lower().rstrip() == "y":
                        user_input = "GENERATE NEXT COMMAND JSON"
                        break
                    elif console_input.lower().startswith("y -"):
                        try:
                            self.next_action_count = abs(
                                int(console_input.split(" ")[1])
                            )
                            user_input = "GENERATE NEXT COMMAND JSON"
                        except ValueError:
                            print(
                                "Invalid input format. Please enter 'y -n' where n is"
                                " the number of continuous tasks."
                            )
                            continue
                        break
                    elif console_input.lower() == "n":
                        user_input = "EXIT"
                        break
                    else:
                        user_input = console_input
                        command_name = "human_feedback"
                        break

                if user_input == "GENERATE NEXT COMMAND JSON":
                    logger.typewriter_log(
                        "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
                        Fore.MAGENTA,
                        "",
                    )
                elif user_input == "EXIT":
                    print("Exiting...", flush=True)
                    break
            else:
                # Print command
                logger.typewriter_log (
                    "NEXT ACTION: ",
                    Fore.CYAN,
                    f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}"
                    f"  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
                )

            # Execute command
            if command_name is not None and command_name.lower().startswith("error"):
                result = (
                    f"Command {command_name} threw the following error: {arguments}"
                )
            elif command_name == "human_feedback":
                result = f"Human feedback: {user_input}"
            else:
                result = (
                    f"Command {command_name} returned: "
                    f"{await execute_command(self, command_name, arguments)}"
                )
                if self.next_action_count > 0:
                    self.next_action_count -= 1

            memory_to_add = (
                f"Assistant Reply: {assistant_reply} "
                f"\nResult: {result} "
                f"\nHuman Feedback: {user_input} "
            )

            self.memory.add(memory_to_add)

            # Check if there's a result from the command append it to the message
            # history
            if result is not None:
                self.full_message_history.append(create_chat_message("system", result))
                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
            else:
                self.full_message_history.append(
                    create_chat_message("system", "Unable to execute command")
                )
                logger.typewriter_log(
                    "SYSTEM: ", Fore.YELLOW, "Unable to execute command"
                )

            self.organization.update_status(self.ai_id, "working on loop " + str(loop_count))
            await asyncio.sleep(1)


    async def dice_roll(self):
        """Rolls a dice and returns the result"""
        return random.randint(1, 5)


    async def random_budget(self):
        """ Creates an abitrary budget to give to an agent"""
        return random.randint(1000, 100000)


    async def send_event(self, event_type, *args):
        event_id = uuid.uuid4()
        event = Event(event_id, self, event_type, *args)
        await self.organization.event_queue.put(event)  # Put the event object into the queue
        return event_id


    async def start_test_loop(self, termination_event):
        print(f"\033[31m\n ******************** Starting interaction loop of agent: {self.ai_name} ******************\033[0m")
        # Interaction Loop

        # initialize the agents status
        await self.send_event("update_agent_status", self.ai_id, "starting interaction loop")

        while not self.terminated:
            print(f"[start_test_loop] Agent {self.ai_name} starting loop iteration...")
            # Gracefully shut down agent whenever python is closed down. 
            print(f"[start_test_loop] Agent {self.ai_name} termination_event.is_set(): {termination_event.is_set()}")
            if termination_event.is_set():
                print(f"\033[31m\n ******************** Terminating agent: {self.ai_name} ******************\033[0m")
                self.terminated = True
                break

            try:
                # Add a timeout to the blocking operation
                dice_result = await asyncio.wait_for(self.dice_roll(), timeout=1.0)
            except asyncio.TimeoutError:
                # If the operation times out, continue to the next iteration to check for termination
                continue

            self.loop_count += 1
            await self.update_agent_config(loop_count=self.loop_count)
            print(f"\033[32m\n\n ****** Starting agent {self.ai_name} loop {self.loop_count} ******\033[0m")

            # Get a random dice result
            dice_result = await self.dice_roll()

            # Calculate the current agent operating costs
            event_id = await self.send_event("calculate_operating_cost_of_agent", self.ai_id)
            agent_operating_costs = await self.organization.get_event_result(event_id)
            print(f"agent operating costs: {agent_operating_costs}")

            # Update the running costs in the yaml
            await self.send_event("update_agent_running_cost", self.ai_id, agent_operating_costs)

            # Update the agent budget
            await self.send_event("update_agent_budget", self.ai_id, agent_operating_costs)

            # Receive message and build status update
            message_event_id = await self.send_event("receive_message", self.ai_id)
            message = await self.organization.get_event_result(message_event_id)

            # Build the status udpate of the agent to add to prompt 
            status_event_id = await self.send_event("build_status_update", self.ai_id)
            agent_status = await self.organization.get_event_result(status_event_id)
            print("agent status: ", agent_status)

            # Build an arbitrary status
            status = f"agent {self.ai_name} is in loop {self.loop_count} rolled {dice_result}"

            # Update the agent status
            await self.send_event("update_agent_status", self.ai_id, status)

            if dice_result == 1:
                next_free_id = len(self.organization.agents)
                name = f"staff_{next_free_id}"

                # Create arbitrary goals and roles
                goals = ''.join(random.choices(string.ascii_lowercase, k=10))
                role = ''.join(random.choices(string.ascii_lowercase, k=10))

                # Create an arbitrary budget
                my_budget = self.organization.agent_budgets.get(self.ai_id)
                staff_budget = my_budget * random.uniform(0, 1)

                event_id = await self.send_event("hire_staff", name, role, goals, staff_budget, self.ai_name, self.ai_id)
                response = await self.organization.get_event_result(event_id)
                print(f"response: {response}")
                await asyncio.sleep(1)

            elif dice_result == 2:
                # staff_members = await self.organization.get_staff(self.ai_id)

                # if len(staff_members) == 0:
                #     print(f"agent {self.ai_name} has no staff members to message in loop {self.loop_count}")
                #     continue

                # random_staff_member = random.choice(staff_members)
                # message = f"test message from agent {self.ai_name} to agent {random_staff_member} in loop {self.loop_count}"
                
                
                # event_id = await self.send_event("message_staff", self.ai_id, random_staff_member.ai_id, message)
                # response = await self.organization.get_event_result(event_id)

                # print(f"agent {self.ai_name} messaged staff member {random_staff_member} in loop {self.loop_count}")
                # print(f"response: {response}")
                await asyncio.sleep(2)


            elif dice_result == 3:
                # message = f"i am {self.ai_name} and iam messaging you in loop {self.loop_count}"
                # event = await self.send_event("message_supervisor", self.ai_id, message)
                # response = event.result
                # print(f"agent {self.ai_name} messaged supervisor in loop {self.loop_count}")
                # print(f"response: {response}")
                await asyncio.sleep(3)

            elif dice_result == 4:
                # event = await self.send_event("random_action")
                # response = event.result
                # print(f"agent {self.ai_name} did a random action in loop {self.loop_count}")
                #  print(f"response: {response}")
                await asyncio.sleep(4)

            elif dice_result == 5:
                # staff_members = await self.organization.get_staff(self.ai_id)
                # if len(staff_members) == 0:
                #     print(f"agent {self.ai_name} has no staff members to fire in loop {self.loop_count}")
                #     continue
                # random_staff_member = random.choice(staff_members)
                # event_id = await self.send_event("fire_staff", random_staff_member.ai_id)
                # response = await self.organization.get_event_result(event_id)
                # print(f"agent {self.ai_name} fired staff member {random_staff_member} in loop {self.loop_count}")
                # print(f"response: {response}")
                await asyncio.sleep(5)

        print(f"\033[31m\n ******************** Agent {self.ai_name} loop terminated ******************\033[0m")

    async def start_test_loop_dec(self):
        print(f"\033[31m\n ******************** Starting interaction loop of agent: {self.ai_name} ******************\033[0m")
        # Interaction Loop
        
        # initialize the agents status
        await self.organization.update_agent_status(self.ai_id, "starting interaction loop")
        

        while not self.terminated:
            self.loop_count += 1
            await self.update_agent_config(loop_count=self.loop_count)
            print(f"\033[32m\n\n ****** Starting agent {self.ai_name} loop {self.loop_count} ******\033[0m")

            # Get a random dice result
            dice_result = await self.dice_roll()
            
            # Calculate the current agent operating costs
            agent_operating_costs = await self.organization.calculate_operating_cost_of_agent(self.ai_id)
            print(f"agent operating costs: {agent_operating_costs}")

            # Update the runnning costs in the yaml
            await self.organization.update_agent_running_cost(self.ai_id, agent_operating_costs)

            # Update the agent budget
            await self.organization.update_agent_budget(self.ai_id, agent_operating_costs)

            # Recieve message and build status update
            message = await self.organization.receive_message(self.ai_id)
            agent_status = await self.organization.build_status_update(self.ai_id)
            status = f"agent {self.ai_name} is in loop {self.loop_count} rolled {dice_result}"


            # Update the agent status
            await self.organization.update_agent_status(self.ai_id, status)

            print(f"agent {self.ai_name} status update: {agent_status}")
            print(f"agent {self.ai_name} received message: {message}")
            print(f"agent dice results {dice_result}")

            if dice_result == 1:
                next_free_id = len(self.organization.agents)
                name = f"staff_{next_free_id}"

                # Create arbitrary goals and roles
                goals = ''.join(random.choices(string.ascii_lowercase, k=10))
                role = ''.join(random.choices(string.ascii_lowercase, k=10))

                # Create an arbitrary budget
                my_budget = self.organization.agent_budgets.get(self.ai_id)
                staff_budget = my_budget * random.uniform(0, 1)

                response = await self.organization.hire_staff(
                    name, role, goals, staff_budget, self.ai_name, self.ai_id
                )

                print(f"agent {self.ai_name} hired staff member {name} in loop {self.loop_count}")
                print(f"response: {response}")
                await asyncio.sleep(1)

            elif dice_result == 2:
                # Message a random staff member
                staff_members = await self.organization.get_staff(self.ai_id)

                if len(staff_members) == 0:
                    print(f"agent {self.ai_name} has no staff members to message in loop {self.loop_count}")
                    continue
                
                random_staff_member = random.choice(staff_members)
                print("random staff members", random_staff_member.ai_id)
                response = await self.organization.message_staff(self.ai_id, random_staff_member.ai_id, f"test message from agent {self.ai_name} to agent {random_staff_member} in loop {self.loop_count}")
                print(f"agent {self.ai_name} messaged staff member {random_staff_member} in loop {self.loop_count}")
                print(f"response: {response}")
                await asyncio.sleep(2)

            elif dice_result == 3:
                # Message a superviso
                response = await self.organization.message_supervisor(self.ai_id, f"i am { self.ai_name} and iam messaging you in loop {self.loop_count}")
                print(f"agent {self.ai_name} messaged supervisor in loop {self.loop_count}")
                print(f"response: {response}")
                await asyncio.sleep(3)

            elif dice_result == 4:
                # Change agent status to arbitrary letter of the alphabet
                # Get arbitrary letter of the alphabet
                # await asyncio.sleep(4)
                print (f"agent {self.ai_name} did a random action in loop {self.loop_count}")

            elif dice_result == 5:
               # Get random staff member
               staff_members = await self.organization.get_staff(self.ai_id)
               if len(staff_members) == 0:
                   print(f"agent {self.ai_name} has no staff members to fire in loop {self.loop_count}")
                   continue
               # pick random one
               random_staff_member = random.choice(staff_members)
               response = await self.organization.fire_staff(random_staff_member.ai_id)        
               print(f"agent {self.ai_name} fired staff member {random_staff_member} in loop {self.loop_count}")
               print(f"response: {response}")
               await asyncio.sleep(5)
        
        print(f"\033[31m\n ******************** Agent {self.ai_name} loop terminated ******************\033[0m")


            

        


    