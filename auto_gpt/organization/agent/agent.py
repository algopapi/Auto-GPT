from colorama import Fore, Style
from collections import deque
from typing import List


from auto_gpt.data.prompts.response_prompt import Thought, Command
import auto_gpt.chat as chat
import auto_gpt.commands as cmd
from auto_gpt.config import Config
from auto_gpt.utils.print_utils import (
    print_to_console,
    print_assistant_thoughts,
)
from auto_gpt.memory import get_memory
from auto_gpt.data.prompts.response_prompt import load_prompt
from auto_gpt.data.output_parsers.pydantic_parser import parse
from auto_gpt.spinner import Spinner


DEF_USER_INPUT = (
    "Determine which next command to use, and respond using the format specified above:"
)

DEF_EMPLOYEE_DESCRIPTION = """an employee of {agent_supervisor}. You are tasked with: {agent_task}.
Your decisions must be made as independantly as possible and you should report any issues, updates, or answers to your supervisor.
You can do this by messaging your supervisor."""


class Agent:
    def __init__(self, organization, agent_config):
        self.organization = organization
        self.cfg = agent_config
        self.global_cfg = Config()

        self.prompt = self.construct_prompt()

        self.memory = get_memory(self.global_cfg, init=True)
        self.full_message_history = []

        self.staff: List[Agent] = []  # List of workers that work for the agent
        self.pending_messages = (
            deque()
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
            supervisor_name=self.cfg.name,
            founder=False,
        )
        return self.add_staff(new_employee)

    def add_staff(self, new_employee):
        self.staff.append(new_employee)
        return f"Succefully created employee with name:{new_employee.cfg.name}, task: {new_employee.cfg.task}, and goals: {new_employee.cfg.goals}\n"

    def message_staff(self, name, message):
        self.organization.route_message(self, self.organization.agents[name], message)
        return f"Succefully sent message to employee {name}\n"

    def list_staff(self):
        employee_list = ""
        for employee in self.staff:
            employee_list += (
                f"coworker name:{employee.cfg.name}, task:{employee.cfg.task}\n"
            )

        return employee_list

    def fire_staff(self, name):
        if self.organization.remove_agent(name):
            return f"Succefully removed employee with name:{name}\n"
        return f"Failed to remove employee with name:{name}\n"

    def message_supervisor(self, message):
        """
        Auto routes a message from the staff member to the supervisor
        """
        self.organization.route_message(
            self, self.organization.agents[self.cfg.supervisor_name], message
        )
        return f"Succesfully sent message to supervisor {self.cfg.supervisor_name}\n"

    def recieve_message(self, sender, message):
        print(
            f"Agent {self.cfg.name} recieved message from {sender.name}. Message = {message}"
        )
        self.pending_messages.append((sender.name, message))
        print(f"\nAgent {self.cfg.name} pending responses: {self.pending_messages}\n")
        pass

    def step(self):
        # Append staff info to the prompt
        staff_info = self.build_status_update()
        self.prompt += "\n" + staff_info

        # Append next pending messages to the agent context
        if self.pending_messages:
            message = self.pending_messages.popleft()
            agent_name, agent_message = message
            user_input = f"Incoming Message from {agent_name}:{agent_message}"
        else:
            user_input = DEF_USER_INPUT
        with Spinner("Thinking... "):
            assistant_reply = chat.chat_with_ai(
                self.prompt,
                user_input,
                self.full_message_history,
                self.memory,
                self.global_cfg.fast_token_limit,
                self.global_cfg.debug_mode,
            )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument
        # 1. Parse thought and get status
        parse_thought_result = parse(assistant_reply, Thought)
        if parse_thought_result.success:
            thought = parse_thought_result.result
            self.cfg.status = thought.status
            print_assistant_thoughts(self.cfg.name, thought, self.global_cfg.speak_mode)
        else:
            print_to_console(
                "Error parsing Thoughts: \n",
                Fore.RED,
                parse_thought_result.error_message,
            )

        # 2. Parse and execute command
        parse_command_result = parse(assistant_reply, Command)
        result = ""
        if parse_command_result.success:
            command = parse_command_result.result
            print_to_console(
                "NEXT ACTION:",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command.name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{command.args}{Style.RESET_ALL}",
            )
            execute_command = True
            if not self.global_cfg.continuous_mode:
                # User authorization: Prompt the user to press y/n to continue or leave.
                print(
                    f"Enter 'y' to authorise command, 'n' to exit program, or write your response to interact with {self.cfg.name}...",
                    flush=True,
                )
                console_input = input(Fore.MAGENTA + "Input:" + Style.RESET_ALL)

                # Accept, reject or give feedback.
                if console_input.lower() == "y":
                    message = "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-="
                    print_to_console(
                        message,
                        Fore.MAGENTA,
                        "",
                    )
                elif console_input.lower() == "n":
                    print("Exiting...", flush=True)
                    return
                else:
                    result = f"Human feedback: {console_input}"
                    execute_command = False  # Canceled by human feedback

            if execute_command:
                result = f"Command {command.name} returned: {cmd.execute_command(self, command.name, command.args)}"
        else:
            # Send result as error.
            result = parse_command_result.error_message
            print_to_console("Error parsing Command: \n", Fore.RED, result)

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
            staff_info += f"{self.staff.index(staff) + 1}. Name: {staff.cfg.name}, Task: {staff.cfg.task}, Status: {staff.cfg.status}\n"
        print(staff_info)
        return staff_info
