"""Main script for the autogpt package."""
import asyncio
import logging
import signal
from contextlib import suppress

from colorama import Fore

#from autogpt.agent.agent import Agent
#from autogpt.memory import get_memory
from autogpt.args import parse_arguments
from autogpt.config import Config, check_openai_api_key
from autogpt.logs import logger
from autogpt.organization.initialize_org import get_organization

# Load environment variables from .env file

async def main() -> None:
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

if __name__ == "__main__":
    asyncio.run(main())