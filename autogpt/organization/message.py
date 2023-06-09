from typing import List, Optional, Union

from autogpt.config.config import Singleton


class Message:
    def __init__(self, message: str, message_id: int, sender_id: int, receiver_id: int, from_supervisor: bool):
        self.message = message
        self.message_id = message_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.from_supervisor = from_supervisor
        self.read = False
        self.responded = False
        self.response = None   # Include a field for the response as well.

    def set_read(self) -> None:
        self.read = True
    
    def set_responded(self) -> None:
        self.responded = True

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
        message_prompt= f"m_id-{self.message_id}: Incoming message from {self.sender_id} : {self.message} \n"
        message_prompt += f"Respond to message using the `respond_to_messge` command"

        return message_prompt

class MessageCenter(metaclass=Singleton):
    def __init__(self):
        self.messages = {}

    def store_message(self, message: Message) -> None:
        self.messages[message.message_id] = message

    def fetch_message_by_id(self, message_id: int) -> Optional[Message]:
        return self.messages.get(message_id)

    def remove_message_by_id(self, message_id: int) -> bool:
        if message_id in self.messages:
            del self.messages[message_id]
            return True
        return False
    
    def get_free_message_id(self) -> int:
        """ 
            Find the smalles available message id and return it. 
        """

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

    def fetch_prioritized_response_target(self, receiver_id: int) -> Optional[str]:
        """ 
            Get the message to respond to for a given receiver_id
        """
        unresponded_messages = self.get_unresponded_messages_by_receiver(receiver_id)
        if len(unresponded_messages) == 0:
            return None
        
        prioritized_by_supervisor = self.filter_from_supervisor(unresponded_messages)
        if len(prioritized_by_supervisor) > 0:
            return self.get_message_prompt(prioritized_by_supervisor[0])
        
        return self.get_message_prompt(unresponded_messages[0])

   
    def check_message_belongs_to_sender(self, message_id: int, sender_id: int) -> bool:
        """ 
            Check if a given message belongs to a given sender
        """
        message = self.fetch_message_by_id(message_id)
        if message is not None:
            return message.sender_id == sender_id
        return False
    
    
    def set_response(self, message_id: int, response: str) -> Union[Optional[Message], str]:
        """ 
            Set the response for a given message_id
        """
        message = self.fetch_message_by_id(message_id)
        if message is not None:
            message.set_response(response)
            return message
        else:
            return "Message not found. You probably used the wrong message_id."
