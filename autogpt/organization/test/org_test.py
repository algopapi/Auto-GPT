import asyncio
import unittest
from pathlib import Path

from autogpt.agent.agent import Agent
from autogpt.commands.file_operations import (
    append_to_file,
    list_agent_files,
    write_to_file,
)
from autogpt.config import Config
from autogpt.configurator import create_config
from autogpt.organization.organization import Organization
from autogpt.workspace import Workspace


class TestFileSharing(unittest.TestCase):
    def setUp(self):
        cfg = Config()
        create_config(
            cfg,
            continuous=True,
            continuous_limit=10,
            ai_settings_file="ai_settings.yaml",
            prompt_settings_file="prompt_settings.yaml",
            skip_reprompt=False,
            speak=False,
            debug=True,
            gpt3only=False,
            gpt4only=False,
            memory_type="json_file",
            browser_name="chrome",
            allow_downloads=False,
            skip_news=True,
        )
        # TODO: have this directory live outside the repository (e.g. in a user's
        #   home directory) and have it come in as a command line argument or part of
        #   the env file.
        workspace_directory = None

        if workspace_directory is None:
            workspace_directory = Path(__file__).parent/"my_test_organizations"
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
        

        # Create the organization
        self.org = Organization.create(name="Test Org", goal="Test Goal", initial_budget=1000)
        
        self.founder = self.org.create_agent(
            name="Test Founder",
            role="Test Role",
            goals=["Test Goal 1", "Test Goal 2"],
            founder=True,
            initial_budget=1000
        )

        asyncio.run(self.org.hire_staff(
            name="Test Staff",
            role="Test Role",
            goals="Test Goal",
            budget="500",
            supervisor_id=self.founder.ai_id
        ))


        staff_members = asyncio.run(self.org.get_staff(self.founder.ai_id))
        self.agent_2 = staff_members[0]

    def test_file_sharing(self):

        print(f"\n\n{self.agent_2.workspace_path}")
        # Employee creates a file
        write_to_file_result = write_to_file(f"{self.agent_2.workspace_path}/test_file.txt", "This is a test written by agent 2", self.agent_2)
        print("write_to_file_result: ", write_to_file_result)

        list_agent_files_result = list_agent_files(self.agent_2.ai_id, self.founder)
        print("list_agent_files_result: ", list_agent_files_result)

        write_to_file_2_result = append_to_file(f"{self.agent_2.workspace_path}/test_file.txt", "\nThis is a test written by the founder", self.founder)
        print("write_to_file_2_result: ", write_to_file_2_result)


    def test_converstation_history(self):

        asyncio.run(self.org.message_agent(
            sender_id=self.founder.ai_id,
            receiver_id=str(self.agent_2.ai_id),
            message="Hello, this is a test message from the founder",
        ))

        asyncio.run(self.org.message_agent(
            sender_id=self.founder.ai_id,
            receiver_id=str(self.agent_2.ai_id),
            message="Hello, this is a second message from the founder",
        ))

        asyncio.run(self.org.respond_to_message(
            sender_id=self.agent_2.ai_id,
            message_id="1",
            response="Hey, this is a test response from the employee"
        ))

        conversation_history = asyncio.run(self.org.message_center.generate_conversation_prompt(self.founder.ai_id, self.agent_2.ai_id))
        print(f"\n\nconversation_history:\n{conversation_history}\n\n")




if __name__ == "__main__":
    unittest.main()