import json
import logging
from collections import deque
from typing import List

from colorama import Fore, Style

import auto_gpt.chat as chat
import auto_gpt.commands as cmd
import auto_gpt.speak as speak
from auto_gpt import speak
from auto_gpt.config import Config
from auto_gpt.data.prompts.response_prompt import load_prompt
from auto_gpt.json_parser import fix_and_parse_json
from auto_gpt.logger import logger
from auto_gpt.memory import get_memory
from auto_gpt.spinner import Spinner
from auto_gpt.utils.clean_input import clean_input
from auto_gpt.utils.print_utils import (print_assistant_thoughts,
                                        print_to_console)

global_config = Config()

DEF_USER_INPUT = (
    "Determine which next command to use, and respond using the format specified above:"
)

DEF_EMPLOYEE_DESCRIPTION = """an employee of {agent_supervisor}. You are tasked with: {agent_task}.
Your decisions must be made as independantly as possible and you should report any issues, updates, or answers to your supervisor.
You can do this by messaging your supervisor."""

def attempt_to_fix_json_by_finding_outermost_brackets(json_string):
    # if cfg.speak_mode and cfg.debug_mode:
    #   speak.say_text("I have received an invalid JSON response from the OpenAI API. Trying to fix it now.")
    logger.typewriter_log("Attempting to fix JSON by finding outermost brackets\n")

    try:
        # Use regex to search for JSON objects
        import regex
        json_pattern = regex.compile(r"\{(?:[^{}]|(?R))*\}")
        json_match = json_pattern.search(json_string)

        if json_match:
            # Extract the valid JSON object from the string
            json_string = json_match.group(0)
            logger.typewriter_log(title="Apparently json was fixed.", title_color=Fore.GREEN)
            # if cfg.speak_mode and cfg.debug_mode:
            #    speak.say_text("Apparently json was fixed.")
        else:
            raise ValueError("No valid JSON object found")

    except (json.JSONDecodeError, ValueError) as e:
        # if cfg.speak_mode:
        #     speak.say_text("Didn't work. I will have to ignore this response then.")
        logger.error("Error: Invalid JSON, setting it to empty JSON now.\n")
        json_string = {}

    return json_string


def print_assistant_thoughts(ai_name, assistant_reply):
    """Prints the assistant's thoughts to the console"""
    try:
        try:
            # Parse and print Assistant response
            assistant_reply_json = fix_and_parse_json(assistant_reply)
        except json.JSONDecodeError as e:
            logger.error("Error: Invalid JSON in assistant thoughts\n", assistant_reply)
            assistant_reply_json = attempt_to_fix_json_by_finding_outermost_brackets(assistant_reply)
            assistant_reply_json = fix_and_parse_json(assistant_reply_json)

        # Check if assistant_reply_json is a string and attempt to parse it into a JSON object
        if isinstance(assistant_reply_json, str):
            try:
                assistant_reply_json = json.loads(assistant_reply_json)
            except json.JSONDecodeError as e:
                logger.error("Error: Invalid JSON\n", assistant_reply)
                assistant_reply_json = attempt_to_fix_json_by_finding_outermost_brackets(assistant_reply_json)

        assistant_thoughts_reasoning = None
        assistant_thoughts_plan = None
        assistant_thoughts_speak = None
        assistant_thoughts_criticism = None
        assistant_thoughts = assistant_reply_json.get("thought", {})
        assistant_thoughts_text = assistant_thoughts.get("text")

        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")
            assistant_thoughts_speak = assistant_thoughts.get("speak")

        logger.typewriter_log(f"{ai_name.upper()} THOUGHTS:", Fore.YELLOW, assistant_thoughts_text)
        logger.typewriter_log("REASONING:", Fore.YELLOW, assistant_thoughts_reasoning)

        if assistant_thoughts_plan:
            logger.typewriter_log("PLAN:", Fore.YELLOW, "")
            # If it's a list, join it into a string
            if isinstance(assistant_thoughts_plan, list):
                assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
            elif isinstance(assistant_thoughts_plan, dict):
                assistant_thoughts_plan = str(assistant_thoughts_plan)

            # Split the input_string using the newline character and dashes
            lines = assistant_thoughts_plan.split('\n')
            for line in lines:
                line = line.lstrip("- ")
                logger.typewriter_log("- ", Fore.GREEN, line.strip())

        logger.typewriter_log("CRITICISM:", Fore.YELLOW, assistant_thoughts_criticism)
        # Speak the assistant's thoughts

        return assistant_reply_json
    except json.decoder.JSONDecodeError as e:
        logger.error("Error: Invalid JSON\n", assistant_reply)
      

    # All other errors, return "Error: + error message"
    except Exception as e:
        call_stack = traceback.format_exc()
        logger.error("Error: \n", call_stack)



class Agent:
    def __init__(self, organization, agent_config):
        self.organization = organization
        self.cfg = agent_config
        self.agent_id = self.cfg.agent_id
        self.agent_name = self.cfg.name
        self.supervisor_name = self.cfg.supervisor_name
        self.supervisor_id = self.cfg.supervisor_id
        self.global_cfg = Config()

        self.prompt = self.construct_prompt()

        self.memory = get_memory(self.global_cfg, self.organization.name, self.cfg, init=self.cfg.init_memory) # Dont Clear here
        self.full_message_history = []

        self.staff: List[Agent] = []  # List of workers that work for the agent
        self.pending_messages = (
            deque(self.cfg.pending_messages)
        )  # List of responses that the agent should deal with

    def construct_prompt(self):
        ai_description_dict = {
            "ai_name": self.cfg.name,
            "ai_goals": self.cfg.goals,
        }
        if self.cfg.founder:  # Head of the org
            ai_description_dict["ai_role"] = self.cfg.task
        else:  # organization coworker
            ai_description_dict["ai_role"] = DEF_EMPLOYEE_DESCRIPTION.format(
                agent_supervisor=self.cfg.supervisor_name, agent_task=self.cfg.task
            )
        return load_prompt(ai_description_dict)

    def create_employee(self, name, task, goals):
        new_employee = self.organization.create_agent(
            name=name,
            task=task,
            goals=goals,
            supervisor_name=self.agent_name,
            supervisor_id=self.agent_id,
            founder=False,
        )
        return self.add_staff(new_employee)

    def add_staff(self, new_employee):
        self.staff.append(new_employee)
        return f"Succefully created employee with name:{new_employee.cfg.name}, task: {new_employee.cfg.task}, and goals: {new_employee.cfg.goals}\n"

    def message_staff(self, agent_id, message):

        try:
            agent_id = int(agent_id)
        except ValueError:
            return "You're likely entering the employee name as agent_id, please enter a valid integer agent_id"
        
        print(" MESSAGIN STAFF", agent_id, message)
        agent_id = int(agent_id)
        print(" agent id as int:", agent_id)
        agent = self.organization.find_agent_by_id(agent_id)
        print(" AGENT FOUND")
        
        if agent:
            print("agent exists")
            self.organization.route_message(self, agent, message)
            return f"Successfully sent message to employee {agent.agent_name}\n"
        else:
            print(" DOOESNT EXIST")
            return f"Failed to send message to employee with Agent_id: {agent_id}\n"
       
    def list_staff(self):
        employee_list = ""
        for employee in self.staff:
            employee_list += (
                f"coworker name:{employee.cfg.name}, task:{employee.cfg.task}\n"
            )

        if not employee_list:
            employee_list = "You currently have no staff in service\n"

        return employee_list

    def fire_staff(self, name):
        if self.organization.remove_agent(name):
            return f"Succefully removed employee with name:{name}\n"
        return f"Failed to remove employee with name:{name}\n"

    def message_supervisor(self, message):
        """
        Auto routes a message from the staff member to the supervisor
        """

        if not self.cfg.founder:
            self.organization.route_message(
                self, self.organization.agents[self.cfg.supervisor_id], message
            )
            return f"Succesfully sent message to supervisor {self.cfg.supervisor_name}\n"
        else: 
            return f"You are the founder and therefore dont have a supervisor!\n"

    def recieve_message(self, sender, message):
        print(
            f"Agent {self.cfg.name} recieved message from {sender.agent_name}. Message = {message}"
        )
        self.pending_messages.append(((sender.agent_id, sender.agent_name), message))
        print(f"\nAgent {self.cfg.name} pending responses: {self.pending_messages}\n")
        pass

    def step(self):
        """ Performs a single step of the agent's thinking process."""
        # Append staff info to the prompt
        staff_info = self.build_status_update()
        self.prompt += "\n" + staff_info

        # Append next pending messages to the agent context
        if self.pending_messages:
            message = self.pending_messages.popleft()
            agent_info, agent_message = message
            user_input = f"Incoming Message from {agent_info[0]}:{agent_info[1]}.Message: {agent_message}"
        else:
            user_input = DEF_USER_INPUT
        with Spinner("Thinking... "):
            assistant_reply = chat.chat_with_ai(
                self.prompt,
                user_input,
                self.full_message_history,
                self.memory,
                self.global_cfg.fast_token_limit,
            )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument
        # 1. Parse thought and get status
        print_assistant_thoughts(self.agent_name, assistant_reply)     
        # Get command name and arguments
        try:
            command_name, arguments = cmd.get_command(attempt_to_fix_json_by_finding_outermost_brackets(assistant_reply))
            if global_config.speak_mode:
                speak.say_text(f"I want to execute {command_name}")
        except Exception as e:
            logger.error("Error: \n", str(e))

        if not global_config.continuous_mode:
            ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
            # Get key press: Prompt the user to press enter to continue or escape
            # to exit
            user_input = ""
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}")
            print(
                f"Enter 'y' to authorise command, 'y -N' to run N continuous commands, 'n' to exit program, or enter feedback for {self.agent_name}...",
                flush=True)
            while True:
                console_input = clean_input(Fore.MAGENTA + "Input:" + Style.RESET_ALL)
                if console_input.lower().rstrip() == "y":
                    user_input = "GENERATE NEXT COMMAND JSON"
                    break
                elif console_input.lower().startswith("y -"):
                    try:
                        user_input = "GENERATE NEXT COMMAND JSON"
                    except ValueError:
                        print("Invalid input format. Please enter 'y -n' where n is the number of continuous tasks.")
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
                "")
            elif user_input == "EXIT":
                print("Exiting...", flush=True)
                return
        else:
            # Print command
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}")
            
        # Execute command
        if command_name is not None and command_name.lower().startswith( "error" ):
            result = f"Command {command_name} threw the following error: " + arguments
        elif command_name == "human_feedback":
            result = f"Human feedback: {user_input}"
        else:
            result = f"Command {command_name} returned: {cmd.execute_command(self, command_name, arguments)}"
            # if next_action_count > 0:
            #     next_action_count -= 1

        # Save assistant reply and result to memory
        self.memory.add(f"Assistant Reply: {assistant_reply} " f"\nResult: {result} ")

        # Append result to the message history
        self.full_message_history.append(chat.create_chat_message("system", result))
        print_to_console("SYSTEM: ", Fore.YELLOW, result)

    def build_status_update(self):
        """
        Staff information screen
        """
        staff_info = "STAFF STATUS: \n\n"
        if len(self.staff) == 0:
            staff_info += "You currently have no staff in service\n"

        for staff in self.staff:
            staff_info += f"Agent_Id:{staff.agent_id}. Agent_Name: {staff.agent_name}, Task: {staff.cfg.task}, Status: {staff.cfg.status}\n"
        print(staff_info)
        return staff_info
