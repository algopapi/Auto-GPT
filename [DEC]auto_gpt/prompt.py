from auto_gpt.promptgenerator import PromptGenerator


def get_prompt(budget, operating_costs):
    """
    This function generates a prompt string that includes various constraints, commands, resources, and performance evaluations.
    Returns:
        str: The generated prompt string.
    """

    # Initialize the PromptGenerator object
    prompt_generator = PromptGenerator()

    # Add constraints to the PromptGenerator object
    prompt_generator.add_constraint("You can only use the resources listed below.")
    prompt_generator.add_constraint(f"You have a budget of ${budget} and operating costs of ${operating_costs} per step. A simple tasks will take around 10 steps. If you run out of budget without accomplashing your task, you will be fired.")
    prompt_generator.add_constraint("You can hire and fire staff members to perform tasks for you. Each staff member costs $100 per step to operate. Assign a budget to staff members so that they can hire staff themselves")
    prompt_generator.add_constraint("~4000 word limit for short term memory. Your short term memory is short, so immediately save important information to files.")
    prompt_generator.add_constraint("If you are unsure how you previously did something or want to recall past events, thinking about similar events will help you remember.")
    prompt_generator.add_constraint('Exclusively use the commands listed in double quotes e.g. "command name"')

    # Define the command list
    commands = [
        ("Google Search", "google", {"input": "<search>"}),
        ("Browse Website", "browse_website", {"url": "<url>", "question": "<what_you_want_to_find_on_website>"}),
        ("Message staff", "message_staff", {"agent_id": "<agent_id>", "message": "<message>"}),
        ("List staff", "list_staff", {}),
        ("Hire staff", "hire_staff", {"name": "<name>", "task": "<short_task_desc>", "goals": "<list_of_agent_goals>", "budget" : "<assign budget to employee (the max amount of budget the employee can spend))>"}),
        ("Fire staff", "fire_staff", {"agent_id": "<agent_id>"}),
        ("Message supervisor", "message_supervisor", {"message": "<message>"}),
        ("Write to file", "write_to_file", {"file": "<file>", "text": "<text>"}),
        ("Read file", "read_file", {"file": "<file>"}),
        ("Append to file", "append_to_file", {"file": "<file>", "text": "<text>"}),
        ("Delete file", "delete_file", {"file": "<file>"}),
        ("Search Files", "search_files", {"directory": "<directory>"}),
        ("Evaluate Code", "evaluate_code", {"code": "<full_code_string>"}),
        ("Get Improved Code", "improve_code", {"suggestions": "<list_of_suggestions>", "code": "<full_code_string>"}),
        ("Write Tests", "write_tests", {"code": "<full_code_string>", "focus": "<list_of_focus_areas>"}),
        ("Execute Python File", "execute_python_file", {"file": "<file>"}),
        ("Execute Shell Command, non-interactive commands only", "execute_shell", { "command_line": "<command_line>"}),
        ("Task Complete (Shutdown)", "task_complete", {"reason": "<reason>"}),
        ("Generate Image", "generate_image", {"prompt": "<prompt>"}),
        ("Do Nothing", "do_nothing", {}),
    ]

    # Add commands to the PromptGenerator object
    for command_label, command_name, args in commands:
        prompt_generator.add_command(command_label, command_name, args)

    # Add resources to the PromptGenerator object
    prompt_generator.add_resource("Devide your task into smaller, simpler subtasks and hire staff to perform these subtasks for you. (each staff member costs $100 per step) Simple tasks require at least 10 steps.")
    prompt_generator.add_resource("Offload work within the available budget. If you run out of budget, you should inform staff member, or even fire them")
    prompt_generator.add_resource("Simple tasks, like looking up information, or reading files, cost 1 step. A single staff member should have a minimum budget to run at least steps")
    prompt_generator.add_resource("Internet access for searches and information gathering.")
    prompt_generator.add_resource("Long Term memory management.")
    prompt_generator.add_resource("GPT-3.5 powered Agents for delegation of simple tasks.")
    prompt_generator.add_resource("File output.")


    # Add performance evaluations to the PromptGenerator object
    prompt_generator.add_performance_evaluation("Continuously review and analyze your actions to ensure you are performing to the best of your abilities.")
    prompt_generator.add_performance_evaluation("Constructively self-criticize your big-picture behavior constantly.")
    prompt_generator.add_performance_evaluation("Reflect on past decisions and strategies to refine your approach.")
    prompt_generator.add_performance_evaluation("Every command takes energy and time, so be smart and  devide tasks among employees if needed")

    # Generate the prompt string
    prompt_string = prompt_generator.generate_prompt_string()

    return prompt_string