import glob
import os
from datetime import datetime
from typing import List, Optional, Union

import aiofiles
import yaml

from autogpt.config.config import Singleton

INBOX_TEMPLATE = """
    YOUR INBOX (priority messages first):

    INCOMING RESPONSES: 
    {incoming_responses}

    NEW INCOMING MESSAGE:
    {incoming_message}
"""


def update_yaml_after_async(func):
    async def wrapper(self, *args, **kwargs):
        res = await func(self, *args, **kwargs)
        # Make sure to call a_save of MessageCenter to update the YAML file.
        await self.a_save()
        return res
    return wrapper

class Message:
    def __init__(
            self,
            message: str,
            message_id: int,
            sender_id: int,
            receiver_id: int,
            from_supervisor: bool,
            response_to_id: Optional[int] = None,
            response_id: Optional[int] = None,
            timestamp: Optional[datetime] = None,
            responded: bool = False, 
            read: bool = False,
        ):

        self.message = message
        self.message_id = message_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.from_supervisor = from_supervisor

        self.response_to_id = response_to_id # If this is a response to a message, store the id of the message here.
        self.response_id = response_id # store the response of this message here.
 
        self.read = read
        self.responded = responded
        self.timestamp = timestamp # Include the timestamp the message was sent at.

    def set_read(self) -> None:
        """
            Set the read flag to true
        """
        self.read = True
    
    def set_responded(self) -> None:
        """ 
            Set the responded flag to true
        """
        self.responded = True

    def set_response_to_id(self, response_to_id: int) -> None:
        """
            Set the id of the message this message is a response to
        """
        self.response_to_id = response_to_id

    def set_response_id(self, response_id: int) -> None:
        """ 
            Set the id of the response to this message
        """
        self.response_id = response_id

    def set_response(self, response: str) -> None:
        """ 
            Set the response for a given message
        """
        self.response = response
        self.set_responded()

    def construct_message_prompt(self) -> str:
        """ 
            Construct the actual message string here. Might do some more interesting stuff later like:
            - Add a timestamp
            - Add the name of the incoming messenger 
            - Other message details
        """
        if self.from_supervisor:
            message_prompt = f"Message ID {self.message_id}: Incoming message from supervisor (ID: {self.sender_id}): {self.message}\n"
        else:
            message_prompt= f"Message ID {self.message_id}: Incoming message from staff member (ID: {self.sender_id}): {self.message}\n"
        return message_prompt


class MessageCenter(metaclass=Singleton):
    def __init__(self, organization):
        self.messages = {}
        self.max_id = 0
        self.organization = organization
        self.message_yaml_path = organization.org_dir_path + "/" + f"{organization.name}_messages.yaml"
        print("message_yaml_path: ", self.message_yaml_path)

    @update_yaml_after_async
    async def add_message(self, message: Message):
        # Logic to add a new message
        self.messages[message.message_id] = message

    async def a_save(self):
        data = {
            'max_id': self.max_id,
            'messages': {message_id: vars(message) for message_id, message in self.messages.items()}
        }
        
        if not os.path.exists(self.message_yaml_path):
            os.makedirs(os.path.dirname(self.message_yaml_path), exist_ok=True)
            
        async with aiofiles.open(self.message_yaml_path, mode='w') as outfile:
            await outfile.write(yaml.dump(data))

    def save(self):
        data = {
            'max_id': self.max_id,
            'messages': {message_id: vars(message) for message_id, message in self.messages.items()}
        }
        
        if not os.path.exists(self.message_yaml_path):
            os.makedirs(os.path.dirname(self.message_yaml_path), exist_ok=True)
        
        with open(self.message_yaml_path, mode='w') as outfile:
            yaml.dump(data, outfile)

    def load_messages(self):
        if not os.path.exists(self.message_yaml_path):
            return

        with open(self.message_yaml_path, mode='r') as infile:
            data = yaml.safe_load(infile.read())
            self.max_id = data.get('max_id', 0)
            self.messages = {message_id: Message(**message_data) for message_id, message_data in data.get('messages', {}).items()}






    async def store_message(self, message: Message) -> None:
        self.messages[message.message_id] = message


    def fetch_message_by_id(self, message_id: int) -> Optional[Message]:
        return self.messages.get(message_id)


    def get_free_message_id(self) -> int:
        """
        Find the smallest available message id and return it. 
        """
        self.max_id += 1
        return self.max_id
    

    def fetch_messages_by_receiver(self, receiver_id: int) -> List[Message]:
        """ 
            Get all messages for a given receiver_id
        """
        return [message for message in self.messages.values() if message.receiver_id == receiver_id]


    def fetch_messages_by_sender(self, sender_id: int) -> List[Message]:
        """ 
            Get all messages for a given sender_id
        """
        return [message for message in self.messages.values() if message.sender_id == sender_id]


    @staticmethod
    def filter_unread_messages(messages: List[Message]) -> List[Message]:
        """ 
            Filter unread messages from a list of messages
        """
        return [message for message in messages if not message.read]


    @staticmethod
    def filter_unresponded_messages(messages: List[Message]) -> List[Message]:
        """ 
            Filter unresponded messages from a list of messages
        """
        return [message for message in messages if not message.responded]


    @staticmethod
    def filter_from_supervisor(messages: List[Message]) -> List[Message]:
        """ 
            Filter messages from supervisor from a list of messages
        """
        return [message for message in messages if message.from_supervisor]


    def get_unresponded_messages_by_receiver(self, receiver_id: int) -> List[Message]:
        """ 
            Get all unresponded messages for a given receiver_id
        """
        receiver_messages = self.fetch_messages_by_receiver(receiver_id)
        return self.filter_unresponded_messages(receiver_messages)


    def get_message_prompt(self, message: Message) -> str:
        """ 
            Get the message prompt for a given message
        """
        return message.construct_message_prompt()
    

    def fetch_conversation(self, sender_id: int, receiver_id: int, last_n: int) -> List[Message]:
        """ 
        Return a list of last_n messages between the sender and receiver. 
        """
        sender_messages = self.fetch_messages_by_sender(sender_id)
        receiver_messages = self.fetch_messages_by_receiver(receiver_id)

        # Filter messages that are between the sender and receiver.
        conversation = [msg for msg in sender_messages if msg.receiver_id == receiver_id]
        conversation += [msg for msg in receiver_messages if msg.sender_id == sender_id]

        # Sort the messages by message_id to maintain the order of conversation
        conversation.sort(key=lambda msg: msg.message_id, reverse=True)

        # Return only the last 'n' messages
        return conversation[:last_n]
    

    async def generate_conversation_prompt(self, sender_id: int, receiver_id: int) -> str:
            """
                Generate a string representation of the last few messages between two users
            """
            messages_between = self.fetch_conversation(sender_id, receiver_id, last_n=8)
            messages_between.sort(key=lambda m: m.timestamp) # Sort messages by timestamp

            if len(messages_between) == 0:
                return f"No conversation history between you and agent:{receiver_id}"

            prompt = f"This is the conversation history between you and agent: {receiver_id}\n"
            
            for message in messages_between:
                sender = "You" if message.sender_id == receiver_id else "Sender ID: "+str(sender_id)
                prompt += f"{sender}: {message.message}\n"

            print(f"Conversation prompt:\n {prompt}")
            return prompt


    def create_message(
            self,
            message: str,
            sender_id: int,
            receiver_id: int,
            from_supervisor: bool,
            message_id: int,
            response_to_id: Optional[int] = None,
            response_id: Optional[int] = None,
            datetime: datetime = datetime.now()
    ):
        return Message(
            message,
            message_id,
            sender_id,
            receiver_id,
            from_supervisor,
            response_to_id,
            response_id,
            datetime
        )

    @update_yaml_after_async
    async def add_new_message(
            self,
            message: str,
            sender_id: int,
            receiver_id: int,
            from_supervisor: bool,
            response_to_id: Optional[int] = None,
            response_id: Optional[int] = None,
        ) -> str:
        """ 
            Add a message to the message center
        """
        timestamp = datetime.now()
        # Find a valid message ID
        message_id = self.get_free_message_id()
        
        message = self.create_message(
            message,
            sender_id,
            receiver_id,
            from_supervisor,
            message_id,
            response_to_id,
            response_id,
            timestamp
        )

        # Store the message
        await self.store_message(message)


    def receive_message(self, agent_id: int) -> str:
        """ 
            Checks pending messages and returnes the prioritized message to the prompt. 
            Unresponded messages from supervisor are prioritized and showed first. 
        """
        agent_messages = self.get_unresponded_messages_by_receiver(agent_id)

        # Filter messages from supervisor
        messages_from_supervisor = self.filter_from_supervisor(agent_messages)


        if len(messages_from_supervisor) > 0:
            prompt = "You have a pending message from your supervisor: \n"
            message = messages_from_supervisor[0]
            message.read = True
            return self.get_message_prompt(message)
        

    async def get_inbox_message_ids(self, agent_id: int) -> List[int]:
        """
            Return a list of message_ids for all messages in the inbox (unresponded messages)
        """
        agent_messages = self.get_unresponded_messages_by_receiver(agent_id)
        inbox_message_ids = [msg.message_id for msg in agent_messages]

        return inbox_message_ids


    async def get_inbox(self, agent_id: int) -> str:
        """
            Construct the inbox for a given agent
            Args:
                agent_id: The agent for which the inbox is to be constructed
            
            Returns:
                A string representation of the inbox
        """        
        # Get all unresponded messages
        unresponded_messages = self.get_unresponded_messages_by_receiver(agent_id)

        # Get message from supervisor first
        messages_from_supervisor = self.filter_from_supervisor(unresponded_messages)

        # delete messages from supervisor from unresponded messages
        unresponded_messages = [msg for msg in unresponded_messages if msg not in messages_from_supervisor]

        # Sort unresponded_messages by timestamp (newest first)
        unresponded_messages.sort(key=lambda msg: msg.timestamp, reverse=True)

        prompt = f"INBOX:\n"
        prompt += f"NEW INCOMING MESSAGES - high priority first\n"

        if len(messages_from_supervisor) > 0:
            for message in messages_from_supervisor:
                prompt += message.construct_message_prompt()

        prompt += f"\n\nINCOMING RESPONSES - high priority first\n"

        if len(unresponded_messages) > 0:
            for message in unresponded_messages:
                prompt += message.construct_message_prompt()

        if len(messages_from_supervisor) + len(unresponded_messages) > 0:
            # there are messages that need possible responding and we should let the agent now how to
            prompt += "\n\nUse the `respond_to_message` command to respond to an incoming message'\n"

        return prompt
    

    def check_message_belongs_to_sender(self, message_id: int, sender_id: int) -> bool:
        """ 
            Check if a given message belongs to a given sender

            Args:
                message_id: The message to check 
                sender_id: The sender to check
            
            Returns:
                True if the message belongs to the sender, False otherwise
        """
        message = self.fetch_message_by_id(message_id)
        if message is not None:
            return message.sender_id == sender_id
        return False
    

    def check_message_adressed_to_reciever(self, message_id: int, receiver_id: int) -> bool:
        """ 
            Check if a given message was addressed to a given receiver

            Args:
                message_id: The message to check
                receiver_id: The receiver to check

            Returns:
                True if the message was addressed to the receiver, False otherwise
        """
        message = self.fetch_message_by_id(message_id)
        if message is not None:
            return message.receiver_id == receiver_id
        return False

    @update_yaml_after_async
    async def respond_to_message(self, message_id: int, response: str, sender_id: int) -> str:
        """
            Respond to a message. 
            Args:
                message_id: The message to respond to
                response: The response to the message
                sender_id: The agent responding to the message 
        """

        # Get the message
        initial_message = self.fetch_message_by_id(message_id)

        # Check if message exists'
        if initial_message is None:
            return "Message does not exist. Please double check the message ID"

        # Check if message belongs to sender
        if not self.check_message_adressed_to_reciever(message_id, sender_id):
            return "Message does not belong to you. Please double check the message ID"

        # Check if message is already responded to
        if initial_message.response_id is not None:
            return "You have already responded to this message."
        
        # Get a new message ID
        message_id = self.get_free_message_id()

        # Check if message is from supervisor (i.e., are you responding to your supervisor?)
        from_supervisor = await self.organization.is_supervisor(initial_message.sender_id, sender_id)
       
        # Create a new message
        message = self.create_message(
            response,
            sender_id,
            initial_message.sender_id,
            from_supervisor, # hmm shouldt his be true or false?
            message_id,
            response_to_id=initial_message.message_id
        )

        # Set the response_id of the original message to the new message id
        initial_message.response_id = message_id
        initial_message.responded = True

        await self.store_message(message)
        return f"Successfully responded to message {message_id}"