"""The application entry point.  Can be invoked by a CLI or any other front end application."""
import asyncio
import logging
import signal
import sys
from pathlib import Path

from colorama import Fore, Style

from autogpt.agent import Agent
from autogpt.commands.command import CommandRegistry
from autogpt.config import Config, check_openai_api_key
from autogpt.configurator import create_config
from autogpt.logs import logger
from autogpt.memory.vector import get_memory
from autogpt.organization.initialize_org import initialize_organization
from autogpt.plugins import scan_plugins
from autogpt.prompts.prompt import DEFAULT_TRIGGERING_PROMPT, construct_main_ai_config
from autogpt.utils import (
    get_current_git_branch,
    get_latest_bulletin,
    get_legal_warning,
    markdown_to_ansi_style,
)
from autogpt.workspace import Workspace
from scripts.install_plugin_deps import install_plugin_dependencies

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


# Load environment variables from .env file

async def startup() -> None:
    """Main function for the script"""
    cfg = Config()
    # TODO: fill in llm values here
    check_openai_api_key()
    parse_arguments()
    logger.set_level(logging.DEBUG if cfg.debug_mode else logging.INFO)
    
    org = await get_organization()

    # Create a task for the org.start() method
    start_task = asyncio.create_task(org.start())

    # Define a signal handler to set the termination event
    def handle_signal(*args):
        print("[handle_signal] Termination signal received. Initiating shutdown...")
        asyncio.create_task(org.shutdown())
        print("[handle_signal] Shutdown process initiated.")

    # Add the signal handler to the event loop
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, handle_signal)

    # Wait for the start task to finish
    await start_task


def run_autogpt_org(
        continuous: bool,
        continuous_limit: int,
        ai_settings: str,
        prompt_settings: str,
        skip_reprompt: bool,
        speak: bool,
        debug: bool,
        gpt3only: bool,
        gpt4only: bool,
        memory_type: str,
        browser_name: str,
        allow_downloads: bool,
        skip_news: bool,
        workspace_directory: str,
        install_plugin_deps: bool,
        organization: bool,
):
    # Configure logging before we do anything else.
    logger.set_level(logging.DEBUG if debug else logging.INFO)
    logger.speak_mode = speak

    cfg = Config()
    # TODO: fill in llm values here
    check_openai_api_key()

    create_config(
        cfg,
        continuous,
        continuous_limit,
        ai_settings,
        prompt_settings,
        skip_reprompt,
        speak,
        debug,
        gpt3only,
        gpt4only,
        memory_type,
        browser_name,
        allow_downloads,
        skip_news,
    )

    if cfg.continuous_mode:
        for line in get_legal_warning().split("\n"):
            logger.warn(markdown_to_ansi_style(line), "LEGAL:", Fore.RED)

    if not cfg.skip_news:
        motd, is_new_motd = get_latest_bulletin()
        if motd:
            motd = markdown_to_ansi_style(motd)
            for motd_line in motd.split("\n"):
                logger.info(motd_line, "NEWS:", Fore.GREEN)
            if is_new_motd and not cfg.chat_messages_enabled:
                input(
                    Fore.MAGENTA
                    + Style.BRIGHT
                    + "NEWS: Bulletin was updated! Press Enter to continue..."
                    + Style.RESET_ALL
                )

        git_branch = get_current_git_branch()
        if git_branch and git_branch != "stable":
            logger.typewriter_log(
                "WARNING: ",
                Fore.RED,
                f"You are running on `{git_branch}` branch "
                "- this is not a supported branch.",
            )
        if sys.version_info < (3, 10):
            logger.typewriter_log(
                "WARNING: ",
                Fore.RED,
                "You are running on an older version of Python. "
                "Some people have observed problems with certain "
                "parts of Auto-GPT with this version. "
                "Please consider upgrading to Python 3.10 or higher.",
            )

    if install_plugin_deps:
        install_plugin_dependencies()


    # TODO: have this directory live outside the repository (e.g. in a user's
    #   home directory) and have it come in as a command line argument or part of
    #   the env file.
    if workspace_directory is None:
        workspace_directory = Path(__file__).parent/"my_organizations"
    else:
        workspace_directory = Path(workspace_directory)
    # TODO: pass in the ai_settings file and the env file and have them cloned into
    #   the workspace directory so we can bind them to the agent.
    workspace_directory = Workspace.make_workspace(workspace_directory)
    cfg.workspace_path = str(workspace_directory)


    # HACK: doing this here to collect some globals that depend on the workspace.
    file_logger_path = workspace_directory / "file_logger.txt"
    if not file_logger_path.exists():
        with file_logger_path.open(mode="w", encoding="utf-8") as f:
            f.write("File Operation Logger ")

    cfg.file_logger_path = str(file_logger_path)

    cfg.set_plugins(scan_plugins(cfg, cfg.debug_mode))
    # Create a CommandRegistry instance and scan default folder
    command_registry = CommandRegistry()

    logger.debug(
        f"The following command categories are disabled: {cfg.disabled_command_categories}"
    )
    enabled_command_categories = [
        x for x in COMMAND_CATEGORIES if x not in cfg.disabled_command_categories
    ]

    logger.debug(
        f"The following command categories are enabled: {enabled_command_categories}"
    )

    for command_category in enabled_command_categories:
        command_registry.import_commands(command_category)

    # ai_name = ""
    # ai_config = construct_main_ai_config()
    # ai_config.command_registry = command_registry
    # if ai_config.ai_name:
    #     ai_name = ai_config.ai_name
    # # print(prompt)
    # # Initialize variables
    # next_action_count = 0

    # add chat plugins capable of report to logger
    if cfg.chat_messages_enabled:
        for plugin in cfg.plugins:
            if hasattr(plugin, "can_handle_report") and plugin.can_handle_report():
                logger.info(f"Loaded plugin into logger: {plugin.__class__.__name__}")
                logger.chat_plugins.append(plugin)

    # Initialize memory and make sure it is empty.
    # this is particularly important for indexing and referencing pinecone memory
    org = initialize_organization()

    # # Create a task for the org.start() method
    # start_task = asyncio.create_task(org.start())

    # # Define a signal handler to set the termination event
    # def handle_signal(*args):
    #     print("[handle_signal] Termination signal received. Initiating shutdown...")
    #     asyncio.create_task(org.shutdown())
    #     print("[handle_signal] Shutdown process initiated.")

    # # Add the signal handler to the event loop
    # loop = asyncio.get_running_loop()
    # loop.add_signal_handler(signal.SIGINT, handle_signal)

    # # Wait for the start task to finish
    # await start_task
    