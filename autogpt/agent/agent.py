import asyncio
import json
import random
import signal
import string
import sys
import uuid
from datetime import datetime

from colorama import Fore, Style

from autogpt.app import execute_command, get_command, get_status
from autogpt.commands.command import CommandRegistry
from autogpt.config import Config
from autogpt.config.ai_config import AIConfig
from autogpt.json_utils.utilities import extract_json_from_response, validate_json
from autogpt.llm.base import ChatSequence
from autogpt.llm.chat import chat_with_ai, create_chat_completion
from autogpt.llm.providers.openai import OPEN_AI_CHAT_MODELS
from autogpt.llm.utils import count_string_tokens
from autogpt.log_cycle.log_cycle import (
    FULL_MESSAGE_HISTORY_FILE_NAME,
    NEXT_ACTION_FILE_NAME,
    PROMPT_SUPERVISOR_FEEDBACK_FILE_NAME,
    SUPERVISOR_FEEDBACK_FILE_NAME,
    USER_INPUT_FILE_NAME,
    LogCycleHandler,
)
from autogpt.logs import logger, print_assistant_thoughts
from autogpt.memory.message_history import MessageHistory
from autogpt.memory.vector import VectorMemory
from autogpt.organization.org_events import Event
from autogpt.speech import say_text
from autogpt.spinner import Spinner
from autogpt.utils import clean_input
from autogpt.workspace import Workspace


class Agent:
    """Agent class for interacting with Auto-GPT.

    Attributes:
        ai_name: The name of the agent.
        memory: The memory object to use.
        next_action_count: The number of actions to execute.
        system_prompt: The system prompt is the initial prompt that defines everything
          the AI needs to know to achieve its task successfully.
        Currently, the dynamic and customizable information in the system prompt are
          ai_name, description and goals.

        triggering_prompt: The last sentence the AI will see before answering.
            For Auto-GPT, this prompt is:
            Determine exactly one command to use, and respond using the format specified
              above:
            The triggering prompt is not part of the system prompt because between the
              system prompt and the triggering
            prompt we have contextual information that can distract the AI and make it
              forget that its goal is to find the next task to achieve.
            SYSTEM PROMPT
            CONTEXTUAL INFORMATION (memory, previous conversations, anything relevant)
            TRIGGERING PROMPT

        The triggering prompt reminds the AI about its short term meta task
        (defining the next task)
    """

    def __init__(
        self,
        memory: VectorMemory,
        next_action_count: int,
        command_registry: CommandRegistry,
        ai_config: AIConfig,
        system_prompt: str,
        triggering_prompt: str,
        workspace_directory: str,
        organization,
        config: Config,
    ):
        self.config = config
        self.ai_config = ai_config
        self.ai_name = ai_config.ai_name
        self.ai_id = ai_config.ai_id
        self.role = ai_config.ai_role
        self.goals = ai_config.ai_goals

        self.memory = memory
        self.history = MessageHistory(self)
        self.next_action_count = next_action_count
        self.command_registry = command_registry
        self.ai_config = ai_config
        self.system_prompt = system_prompt
        self.triggering_prompt = triggering_prompt

        self.workspace = Workspace(workspace_directory, self.config.restrict_to_workspace)
        self.created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.cycle_count = 0
        self.log_cycle_handler = LogCycleHandler()
        self.fast_token_limit = OPEN_AI_CHAT_MODELS.get(
            self.config.fast_llm_model
        ).max_tokens

        self.terminated = ai_config.terminated
        self.loop_count = ai_config.loop_count
        self.founder = ai_config.founder

        self.respone_queue = asyncio.Queue()
        self.organization = organization
  

    async def start_test_loop(self, termination_event):
        await self.send_event("update_agent_status", self.ai_id, "starting interaction loop")

        while not self.terminated:
            # Gracefully shut down agent whenever python is closed down. 
            try:
                # Add a timeout to the blocking operation
                dice_result = await asyncio.wait_for(self.dice_roll(), timeout=1.0)
            except asyncio.TimeoutError:
                # If the operation times out, continue to the next iteration to check for termination
                continue

            self.loop_count += 1
            await self.update_agent_config(loop_count=self.loop_count)

            # Calculate the current agent operating costs
            event_id = await self.send_event("calculate_operating_cost_of_agent", self.ai_id)
            agent_operating_costs = await self.organization.get_event_result(event_id)
            

            # Update the running costs in the yaml
            await self.send_event("update_agent_running_cost", self.ai_id, agent_operating_costs)

            # Update the agent budget
            await self.send_event("update_agent_budget", self.ai_id, agent_operating_costs)

            inbox_prompt_event_id = await self.send_event("get_inbox", self.ai_id)
            inbox_prompt = await self.organization.get_event_result(inbox_prompt_event_id)
            
            print("\033[92m##### START OF INBOX PROMPT OF AGENT {self.ai_name} #####\033[0m")
            print(f"\033[92mInbox prompt = \n {inbox_prompt} \n\033[0m")
            print("\033[92m##### END OF INBOX PROMPT #####\033[0m")
            
            # Build the status udpate of the agent to add to prompt
            status_event_id = await self.send_event("build_status_update", self.ai_id)
            agent_update = await self.organization.get_event_result(status_event_id)
    
            # Build an arbitrary status
            status = f"agent {self.ai_name} is in loop {self.loop_count} rolled {dice_result}"

            # Update the agent status
            await self.send_event("update_agent_status", self.ai_id, status)
            result = None

            if dice_result == 1:
                name = f"staff_hired_by_{self.ai_id}"

                # Create arbitrary goals and roles
                goals = ''.join(random.choices(string.ascii_lowercase, k=10))
                role = ''.join(random.choices(string.ascii_lowercase, k=10))

                # Create an arbitrary budget
                my_budget = self.organization.agent_budgets.get(self.ai_id)
                staff_budget = my_budget * random.uniform(0, 1)

                event_id = await self.send_event("hire_staff", name, role, goals, staff_budget, self.ai_id)
                result = await self.organization.get_event_result(event_id)
                
                await asyncio.sleep(2)

            elif dice_result == 2:
                """ 
                    Message a random staff member
                """
                staff_members = await self.organization.get_staff(self.ai_id)
                supervisor = await self.organization.get_supervisor(self.ai_id)

                if supervisor is not None:
                    staff_members.append(supervisor)

                print("staff_members:", staff_members)

                if len(staff_members) == 0:
                    print(f"agent {self.ai_name} has no staff members to message in loop {self.loop_count}")
                    continue

                random_staff_member = random.choice(staff_members)
                test_message = f"test message from {self.ai_id}:{self.ai_name} to {random_staff_member.ai_id}:{random_staff_member.ai_name} in loop {self.loop_count}"
                event_id = await self.send_event("message_agent", self.ai_id, random_staff_member.ai_id, test_message)
                result = await self.organization.get_event_result(event_id)
                await asyncio.sleep(10)

            elif dice_result == 3:
                """ 
                    This is a random action that would usually be something like using a tool or some other non organization related action.
                """
                result = "random action"
                await asyncio.sleep(5)

            elif dice_result == 4:
                """ 
                    Fire a random staff member
                """
                staff_members = await self.organization.get_staff(self.ai_id)
                if len(staff_members) == 0:
                    #print(f"agent {self.ai_name} has no staff members to fire in loop {self.loop_count}")
                    continue
                random_staff_member = random.choice(staff_members)
                event_id = await self.send_event("fire_staff", random_staff_member.ai_id)
                result = await self.organization.get_event_result(event_id)
                await asyncio.sleep(3)

            elif dice_result == 5:
                """ 
                    Respond to a random message using respond function
                """
                # Get message ids of messages in inbox
                message_id_list = await self.organization.message_center.get_inbox_message_ids(self.ai_id)

                # Pick a random id from the list
                if len(message_id_list) == 0:
                    print("no possible messages to respond to")
                    await asyncio.sleep(1)
                    continue

                print("message_id_list:", message_id_list, "\n")
                # Pick a random message id from the list and create a rtandom response
                random_message_id = random.choice(message_id_list)
                response = f"sending response from agent {self.ai_id}:{self.ai_name} in loop {self.loop_count}"
                # Respond to the message
                event_id = await self.send_event("respond_to_message", str(random_message_id), response, self.ai_id)
                result = await self.organization.get_event_result(event_id)
                await asyncio.sleep(2)

            elif dice_result == 6:
                """ 
                    Get a random converstaion from the message center. 
                """
                staff_members = await self.organization.get_staff(self.ai_id)
                if len(staff_members) == 0:
                    await asyncio.sleep(1)
                    continue
                random_staff_member = random.choice(staff_members)

                # Get the conversation history between you and the random staff member
                event_id = await self.send_event("get_conversation_history", self.ai_id, random_staff_member.ai_id)
                result = await self.organization.get_event_result(event_id)
                print(f"converstation: {response}")

            if result is not None:
                self.history.add("system", result, "action_result")


        print(f"\033[31m\n ******************** Agent {self.ai_id}: {self.ai_name} loop terminated ******************\033[0m")
        await self.organization.notify_termination(self)


    async def update_agent_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.ai_config, key):
                setattr(self.ai_config, key, value)
            else:
                print(f"Unknown attribute '{key}' in AgentConfig.")
        self.ai_config.save()  # Save the updated configuration to the YAML file
        

    async def dice_roll(self):
        """Rolls a dice and returns the result"""
        return random.randint(1, 6)


    async def random_budget(self):
        """ Creates an abitrary budget to give to an agent"""
        return random.randint(1000, 100000)


    async def send_event(self, event_type, *args):
        event_id = uuid.uuid4()
        event = Event(event_id, self, event_type, *args)
        await self.organization.event_queue.put(event)  # Put the event object into the queue
        return event_id


    async def start_interaction_loop(self, termination_event):
        # Interaction Loop
        self.cycle_count = 0
        command_name = None
        arguments = None
        user_input = ""

        # Signal handler for interrupting y -N
        def signal_handler(signum, frame):
            if self.next_action_count == 0:
                sys.exit()
            else:
                print(
                    Fore.RED
                    + "Interrupt signal received. Stopping continuous command execution."
                    + Style.RESET_ALL
                )
                self.next_action_count = 0

        signal.signal(signal.SIGINT, signal_handler)
        
        await self.send_event("update_agent_status", self.ai_id, "starting interaction loop")

        while not self.terminated:
            # Discontinue if continuous limit is reached
            self.cycle_count += 1
            self.log_cycle_handler.log_count_within_cycle = 0
            self.log_cycle_handler.log_cycle(
                self.ai_config.ai_name,
                self.created_at,
                self.cycle_count,
                [m.raw() for m in self.history],
                FULL_MESSAGE_HISTORY_FILE_NAME,
            )
            if (
                self.config.continuous_mode
                and self.config.continuous_limit > 0
                and self.cycle_count > self.config.continuous_limit
            ):
                logger.typewriter_log(
                    "Continuous Limit Reached: ",
                    Fore.YELLOW,
                    f"{self.config.continuous_limit}",
                )
                break

            event_id = await self.send_event("calculate_operating_cost_of_agent", self.ai_id)
            agent_operating_costs = await self.organization.get_event_result(event_id)
            
            await self.send_event("update_agent_running_cost", self.ai_id, agent_operating_costs)
            await self.send_event("update_agent_budget", self.ai_id, agent_operating_costs)
            
            # Receive message and build status update
            inbox_event_id = await self.send_event("get_inbox", self.ai_id)
            inbox = await self.organization.get_event_result(inbox_event_id)

            # Build the status udpate of the agent to add to prompt
            status_event_id = await self.send_event("build_status_update", self.ai_id)
            org_status = await self.organization.get_event_result(status_event_id)

            # Update the current system prompt
            self.system_prompt = self.ai_config.construct_full_prompt(organization=self.organization)

            full_prompt = self.system_prompt + "\n" + org_status + "\n" + inbox
            print("Full system prompt", full_prompt)

            # Send message to AI, get response
            # with Spinner("Thinking... ", plain_output=cfg.plain_output):
            assistant_reply = await chat_with_ai(
                self.config,
                self,
                full_prompt,
                self.triggering_prompt,
                self.fast_token_limit,
                self.config.fast_llm_model,
            )
  
            try:
                assistant_reply_json = extract_json_from_response(assistant_reply)
                validate_json(assistant_reply_json)
            except json.JSONDecodeError as e:
                logger.error(f"Exception while validating assistant reply JSON: {e}")
                assistant_reply_json = {}

            for plugin in self.config.plugins:
                if not plugin.can_handle_post_planning():
                    continue
                assistant_reply_json = plugin.post_planning(assistant_reply_json)

            # Print Assistant thoughts
            if assistant_reply_json != {}:
                # Get command name and arguments
                try:
                    print_assistant_thoughts(
                        self.ai_name, assistant_reply_json, self.config.speak_mode
                    )
                    command_name, arguments = get_command(assistant_reply_json)
                    status = get_status(assistant_reply_json)
                    if self.config.speak_mode:
                        say_text(f"I want to execute {command_name}")

                    arguments = self._resolve_pathlike_command_args(arguments)

                except Exception as e:
                    logger.error("Error: \n", str(e))
                    
            self.log_cycle_handler.log_cycle(
                self.ai_config.ai_name,
                self.created_at,
                self.cycle_count,
                assistant_reply_json,
                NEXT_ACTION_FILE_NAME,
            )

            # First log new-line so user can differentiate sections better in console
            logger.typewriter_log("\n")
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  "
                f"ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
            )

            # Update agent status in the organization
            try :
                event_id = await self.send_event("update_agent_status", self.ai_id, status)
                res = await self.organization.get_event_result(event_id)
            except Exception as e:
                logger.error("Error: \n", str(e))
            

            if not self.config.continuous_mode and self.next_action_count == 0:
                # ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
                # Get key press: Prompt the user to press enter to continue or escape
                # to exit
                self.user_input = ""
                logger.info(
                    "Enter 'y' to authorise command, 'y -N' to run N continuous commands, 's' to run self-feedback commands, "
                    "'n' to exit program, or enter feedback for "
                    f"{self.ai_name}..."
                )
                while True:
                    if self.config.chat_messages_enabled:
                        console_input = clean_input("Waiting for your response...")
                    else:
                        console_input = clean_input(
                            Fore.MAGENTA + "Input:" + Style.RESET_ALL
                        )
                    if console_input.lower().strip() == self.config.authorise_key:
                        user_input = "GENERATE NEXT COMMAND JSON"
                        break
                    elif console_input.lower().strip() == "s":
                        logger.typewriter_log(
                            "-=-=-=-=-=-=-= THOUGHTS, REASONING, PLAN AND CRITICISM WILL NOW BE VERIFIED BY AGENT -=-=-=-=-=-=-=",
                            Fore.GREEN,
                            "",
                        )
                        thoughts = assistant_reply_json.get("thoughts", {})
                        self_feedback_resp = self.get_self_feedback(
                            thoughts, self.config.fast_llm_model
                        )
                        logger.typewriter_log(
                            f"SELF FEEDBACK: {self_feedback_resp}",
                            Fore.YELLOW,
                            "",
                        )
                        user_input = self_feedback_resp
                        command_name = "self_feedback"
                        break
                    elif console_input.lower().strip() == "":
                        logger.warn("Invalid input format.")
                        continue
                    elif console_input.lower().startswith(
                        f"{self.config.authorise_key} -"
                    ):
                        try:
                            self.next_action_count = abs(
                                int(console_input.split(" ")[1])
                            )
                            user_input = "GENERATE NEXT COMMAND JSON"
                        except ValueError:
                            logger.warn(
                                "Invalid input format. Please enter 'y -n' where n is"
                                " the number of continuous tasks."
                            )
                            continue
                        break
                    elif console_input.lower() == self.config.exit_key:
                        user_input = "EXIT"
                        break
                    else:
                        user_input = console_input
                        command_name = "human_feedback"
                        self.log_cycle_handler.log_cycle(
                            self.ai_config.ai_name,
                            self.created_at,
                            self.cycle_count,
                            user_input,
                            USER_INPUT_FILE_NAME,
                        )
                        break

                if user_input == "GENERATE NEXT COMMAND JSON":
                    logger.typewriter_log(
                        "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
                        Fore.MAGENTA,
                        "",
                    )
                elif user_input == "EXIT":
                    logger.info("Exiting...")
                    break
            else:
                # First log new-line so user can differentiate sections better in console
                logger.typewriter_log("\n")
                # Print authorized commands left value
                logger.typewriter_log(
                    f"{Fore.CYAN}AUTHORISED COMMANDS LEFT: {Style.RESET_ALL}{self.next_action_count}"
                )

            # Execute command
            if command_name is not None and command_name.lower().startswith("error"):
                result = f"Could not execute command: {arguments}"
            elif command_name == "human_feedback":
                result = f"Human feedback: {user_input}"
            elif command_name == "self_feedback":
                result = f"Self feedback: {user_input}"
            else:
                for plugin in self.config.plugins:
                    if not plugin.can_handle_pre_command():
                        continue
                    command_name, arguments = plugin.pre_command(
                        command_name, arguments
                    )
                command_result = await execute_command(
                    self.command_registry,
                    command_name,
                    arguments,
                    agent=self,
                )
                result = f"Command {command_name} returned: " f"{command_result}"

                result_tlength = count_string_tokens(
                    str(command_result), self.config.fast_llm_model
                )
                memory_tlength = count_string_tokens(
                    str(self.history.summary_message()), self.config.fast_llm_model
                )
                if result_tlength + memory_tlength + 600 > self.fast_token_limit:
                    result = f"Failure: command {command_name} returned too much output. \
                        Do not execute this command again with the same arguments."

                for plugin in self.config.plugins:
                    if not plugin.can_handle_post_command():
                        continue
                    result = plugin.post_command(command_name, result)
                if self.next_action_count > 0:
                    self.next_action_count -= 1

            # Check if there's a result from the command append it to the message
            # history
            if result is not None:
                self.history.add("system", result, "action_result")
                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
            else:
                self.history.add("system", "Unable to execute command", "action_result")
                logger.typewriter_log(
                    "SYSTEM: ", Fore.YELLOW, "Unable to execute command"
                )
            # add a little cooldown here.
            await asyncio.sleep(1)
        
        # Notify the org agent is terminated
        print(f"\033[31m\n ******************** Agent {self.ai_name} loop terminated ******************\033[0m")
        await self.organization.notify_termination(self)


    def _resolve_pathlike_command_args(self, command_args):
        if "directory" in command_args and command_args["directory"] in {"", "/"}:
            command_args["directory"] = str(self.workspace.root)
        else:
            for pathlike in ["filename", "directory", "clone_path"]:
                if pathlike in command_args:
                    command_args[pathlike] = str(
                        self.workspace.get_path(command_args[pathlike])
                    )
        return command_args


    def get_self_feedback(self, thoughts: dict, llm_model: str) -> str:
        """Generates a feedback response based on the provided thoughts dictionary.
        This method takes in a dictionary of thoughts containing keys such as 'reasoning',
        'plan', 'thoughts', and 'criticism'. It combines these elements into a single
        feedback message and uses the create_chat_completion() function to generate a
        response based on the input message.
        Args:
            thoughts (dict): A dictionary containing thought elements like reasoning,
            plan, thoughts, and criticism.
        Returns:
            str: A feedback response generated using the provided thoughts dictionary.
        """
        ai_role = self.ai_config.ai_role

        feedback_prompt = f"Below is a message from me, an AI Agent, assuming the role of {ai_role}. whilst keeping knowledge of my slight limitations as an AI Agent Please evaluate my thought process, reasoning, and plan, and provide a concise paragraph outlining potential improvements. Consider adding or removing ideas that do not align with my role and explaining why, prioritizing thoughts based on their significance, or simply refining my overall thought process."
        reasoning = thoughts.get("reasoning", "")
        plan = thoughts.get("plan", "")
        thought = thoughts.get("thoughts", "")
        feedback_thoughts = thought + reasoning + plan

        prompt = ChatSequence.for_model(llm_model)
        prompt.add("user", feedback_prompt + feedback_thoughts)

        self.log_cycle_handler.log_cycle(
            self.ai_config.ai_name,
            self.created_at,
            self.cycle_count,
            prompt.raw(),
            PROMPT_SUPERVISOR_FEEDBACK_FILE_NAME,
        )

        feedback = create_chat_completion(prompt)

        self.log_cycle_handler.log_cycle(
            self.ai_config.ai_name,
            self.created_at,
            self.cycle_count,
            feedback,
            SUPERVISOR_FEEDBACK_FILE_NAME,
        )
        return feedback


       