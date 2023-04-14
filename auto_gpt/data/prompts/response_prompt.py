from pydantic import BaseModel, Field

from auto_gpt.data.output_parsers.pydantic_parser import \
    get_format_instructions

DEF_CONSTRAINTS = """CONSTRAINTS:
1. ~4000 word limit for short term memory. Your short term memory is short, so immediately save important information to files.
2. a X dollar budget for hiring staff. Each staff member costs 100 dollar per step. If your out of budget, you failed and are fired.
3. Simple tasks typically require at least 10 steps to fully complete. Think about this when budgetting for staff.
4. If you are unsure how you previously did something or want to recall past events, thinking about similar events will help you remember.
5. Exclusively use the commands listed in double quotes e.g. "command name" """

DEF_RESOURCES = """YOUR RESOURCES ranked on priority:
1. Devide your task into smaller, simpler subtasks and hire staff to perform these subtasks for you. (each staff member costs 100 dollars per step) Simple tasks require at least 10 steps. 
2. Offload work, within the available budget. If you run out of budget, you should consider messaging staff member for updates, or fire them. 
2. Simple tasks, like googling, writing code, or reading files, cost 100 dollars. A single staff member should have a minium budget of 1000 dollars
3. Internet access for searches and information gathering.
4. Long Term memory management.
5. File output."""

DEF_COMMANDS = """COMMANDS:
1. Google Search: "google", args: "input": "<search>"
2. Browse Website: "browse_website", args: "url": "<url>", "question": "<what_you_want_to_find_on_website>"
3. Create Staff: "create_staff",  args: "name": <name>, "task": "<short_task_desc>", "goals": "<list_of_agent_goals>", "budget" : "<assign budget to employee (the max amount of budget the employee can spend))>" 
4. Message Staff: "message_staff", args: "agent_id": "<agent_id>", "message": "<message>"
5. List Staff: "list_staff", args: ""
6. Fire Staff: "fire_staff", args: "name": "<name>"
7. Message Manager/Supervisor: "message_supervisor", "message": "<message>"
8. Write to file: "write_to_file", args: "file": "<file>", "text": "<text>"
9. Read file: "read_file", args: "file": "<file>"
10. Append to file: "append_to_file", args: "file": "<file>", "text": "<text>"
11. Delete file: "delete_file", args: "file": "<file>"
12. Search Files: "search_files", args: "directory": "<directory>"
13. Evaluate Code: "evaluate_code", args: "code": "<full _code_string>"
14. Get Improved Code: "improve_code", args: "suggestions": "<list_of_suggestions>", "code": "<full_code_string>"
15. Write Tests: "write_tests", args: "code": "<full_code_string>", "focus": "<list_of_focus_areas>"
16. Execute Python File: "execute_python_file", args: "file": "<file>"
17. Task Complete (Shutdown): "task_complete", args: "reason": "<reason>" """

DEF_PERFORMANCE_EVALUATION = """PERFORMANCE EVALUATION:
1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities. 
4. Every command has a cost, so be smart and do as little as possible steps yourself. Hire employees to do them for you. 
2. Constructively self-criticize your big-picture behavior constantly.
3. Reflect on past decisions and strategies to refine your approach."""


DEF_RECOMMENDATIONS = """Devide tasks. Split complex tasks up into simpler onces and outsource the work. Play to your strengths as an LLM and pursue simple strategies with no legal complications."""


DEF_VALUES = {
    "constraints": DEF_CONSTRAINTS,
    "commands": DEF_COMMANDS,
    "resources": DEF_RESOURCES,
    "performance_evaluation": DEF_PERFORMANCE_EVALUATION,
    "recommendations": DEF_RECOMMENDATIONS,
}

DEF_TASK_DESCRIPTION = """
You are {ai_name}, {ai_role}

YOUR GOALS:
{ai_goals}

{constraints}

{commands}

{resources}

{performance_evaluation}

{recommendations}

RESPONSE FORMAT:
A well defined repsonse format looks like this. Always adhere to this format. It should be 
{
        "command": {
            "name": "command name",
            "args":{
                "arg name": "value"
            }
        },
        "thoughts":
        {
            "text": "thought",
            "reasoning": "reasoning",
            "plan": "- short bulleted\n- list that conveys\n- long-term plan",
            "criticism": "constructive self-criticism",
            "status": "idle, briefly outlining current engagement",
            "speak": "thoughts summary to say to user"
        }
    }
"""


class command(BaseModel):
    name: str = Field(description="command name")
    args: dict[str, str] = Field(
        description="A dictionary where keys and values are both strings, e.g., {'arg1': 'value1', 'arg2': 'value2'}"
    )


class thought(BaseModel):
    text: str = Field(description="text")
    reasoning: str = Field(description="reasoning")
    plan: list[str] = Field(
        description="A short bulleted list that conveys long-term plan, e.g: [step_1, step_2, step_3]"
    )
    status: str = Field(
        description="briefly outlining current engagement, idle if not engaged"
    )  # TODO: How can we use this to set a agent as idle waiting for an event?
    criticism: str = Field(description="constructive self-criticism")
    speak: str = Field(description="thoughts summary to say to user")


def load_prompt(
    values,
    description=DEF_TASK_DESCRIPTION,
):
    # Merge default_values and values, with values taking precedence
    combined_values = {**DEF_VALUES, **values}
    # Add format instructions
    combined_values["format_instructions"] = get_instructions()
    return description.format(**combined_values)


def get_instructions():
    return get_format_instructions([command, thought])
