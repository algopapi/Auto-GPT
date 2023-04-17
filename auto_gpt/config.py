import abc
import os

import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Singleton(abc.ABCMeta, type):
    """
    Singleton metaclass for ensuring only one instance of a class.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class AbstractSingleton(abc.ABC, metaclass=Singleton):
    pass


class Config(metaclass=Singleton):
    """
    Configuration class to store the state of bools for different scripts access.
    """

    def __init__(self):
        self.temperature = 0.2
        self.continuous_mode = os.getenv("CONTINUOUS", "True") == "True"
        self.speak_mode = os.getenv("SPEAK_MODE", "False") == "True"
        self.debug_mode = os.getenv("DEBUG_MODE", "False") == "True"
        # TODO - make these models be self-contained, using langchain, so we can configure them once and call it good
        self.fast_llm_model = os.getenv("FAST_LLM_MODEL", "gpt-4")
        self.smart_llm_model = os.getenv("SMART_LLM_MODEL", "gpt-4")
        self.fast_token_limit = int(os.getenv("FAST_TOKEN_LIMIT", 4000))
        self.smart_token_limit = int(os.getenv("SMART_TOKEN_LIMIT", 8000))
            

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.use_azure = False
        self.use_azure = os.getenv("USE_AZURE") == "True"
        if self.use_azure:
            self.openai_api_base = os.getenv("OPENAI_API_BASE")
            self.openai_api_version = os.getenv("OPENAI_API_VERSION")
            self.openai_deployment_id = os.getenv("OPENAI_DEPLOYMENT_ID")
            openai.api_type = "azure"
            openai.api_base = self.openai_api_base
            openai.api_version = self.openai_api_version

        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.custom_search_engine_id = os.getenv("CUSTOM_SEARCH_ENGINE_ID")

        self.reflexion_llm_model = os.getenv("FAST_LLM_MODEL", "gpt-3.5-turbo")
        self.reflexion_llm_token_limit = int(os.getenv("SMART_TOKEN_LIMIT", 8000))
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_region = os.getenv("PINECONE_ENV")

        self.image_provider = os.getenv("IMAGE_PROVIDER")
        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        self.huggingface_api_token = os.getenv("HUGGINGFACE_API_TOKEN")

        # User agent headers to use when browsing web
        # Some websites might just completely deny request with an error code if no user agent was found.
        self.user_agent_header = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36"
        }
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = os.getenv("REDIS_PORT", "6379")
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.wipe_redis_on_start = os.getenv("WIPE_REDIS_ON_START", "True") == "True"
        self.memory_index = os.getenv("MEMORY_INDEX", "auto-gpt")
        # Note that indexes must be created on db 0 in redis, this is not configureable.
        self.memory_backend = os.getenv("MEMORY_BACKEND", "local")
        # Initialize the OpenAI API client
        openai.api_key = self.openai_api_key
