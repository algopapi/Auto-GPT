import functools
import time
from typing import List
from unittest.mock import patch

import openai
import openai.api_resources.abstract.engine_api_resource as engine_api_resource
from colorama import Fore, Style
from openai.error import APIError, RateLimitError, Timeout
from openai.openai_object import OpenAIObject

from autogpt.llm.api_manager import ApiManager
from autogpt.llm.base import (
    ChatModelInfo,
    EmbeddingModelInfo,
    MessageDict,
    TextModelInfo,
    TText,
)
from autogpt.logs import logger

OPEN_AI_CHAT_MODELS = {
    info.name: info
    for info in [
        ChatModelInfo(
            name="gpt-3.5-turbo",
            prompt_token_cost=0.002,
            completion_token_cost=0.002,
            max_tokens=4096,
        ),
        ChatModelInfo(
            name="gpt-3.5-turbo-0301",
            prompt_token_cost=0.002,
            completion_token_cost=0.002,
            max_tokens=4096,
        ),
        ChatModelInfo(
            name="gpt-4",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8192,
        ),
        ChatModelInfo(
            name="gpt-4-0314",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8192,
        ),
        ChatModelInfo(
            name="gpt-4-32k",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
        ),
        ChatModelInfo(
            name="gpt-4-32k-0314",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
        ),
    ]
}

OPEN_AI_TEXT_MODELS = {
    info.name: info
    for info in [
        TextModelInfo(
            name="text-davinci-003",
            prompt_token_cost=0.02,
            completion_token_cost=0.02,
            max_tokens=4097,
        ),
    ]
}

OPEN_AI_EMBEDDING_MODELS = {
    info.name: info
    for info in [
        EmbeddingModelInfo(
            name="text-embedding-ada-002",
            prompt_token_cost=0.0004,
            completion_token_cost=0.0,
            max_tokens=8191,
            embedding_dimensions=1536,
        ),
    ]
}

OPEN_AI_MODELS: dict[str, ChatModelInfo | EmbeddingModelInfo | TextModelInfo] = {
    **OPEN_AI_CHAT_MODELS,
    **OPEN_AI_TEXT_MODELS,
    **OPEN_AI_EMBEDDING_MODELS,
}


def meter_api(func):
    """Adds ApiManager metering to functions which make OpenAI API calls"""
    api_manager = ApiManager()

    openai_obj_processor = openai.util.convert_to_openai_object

    def update_usage_with_response(response: OpenAIObject):
        try:
            usage = response.usage
            logger.debug(f"Reported usage from call to model {response.model}: {usage}")
            api_manager.update_cost(
                response.usage.prompt_tokens,
                response.usage.completion_tokens if "completion_tokens" in usage else 0,
                response.model,
            )
        except Exception as err:
            logger.warn(f"Failed to update API costs: {err.__class__.__name__}: {err}")

    def metering_wrapper(*args, **kwargs):
        openai_obj = openai_obj_processor(*args, **kwargs)
        if isinstance(openai_obj, OpenAIObject) and "usage" in openai_obj:
            update_usage_with_response(openai_obj)
        return openai_obj

    def metered_func(*args, **kwargs):
        with patch.object(
            engine_api_resource.util,
            "convert_to_openai_object",
            side_effect=metering_wrapper,
        ):
            return func(*args, **kwargs)

    return metered_func


def retry_api(
    num_retries: int = 10,
    backoff_base: float = 2.0,
    warn_user: bool = True,
):
    """Retry an OpenAI API call.

    Args:
        num_retries int: Number of retries. Defaults to 10.
        backoff_base float: Base for exponential backoff. Defaults to 2.
        warn_user bool: Whether to warn the user. Defaults to True.
    """
    retry_limit_msg = f"{Fore.RED}Error: " f"Reached rate limit, passing...{Fore.RESET}"
    api_key_error_msg = (
        f"Please double check that you have setup a "
        f"{Fore.CYAN + Style.BRIGHT}PAID{Style.RESET_ALL} OpenAI API Account. You can "
        f"read more here: {Fore.CYAN}https://docs.agpt.co/setup/#getting-an-api-key{Fore.RESET}"
    )
    backoff_msg = (
        f"{Fore.RED}Error: API Bad gateway. Waiting {{backoff}} seconds...{Fore.RESET}"
    )

    def _wrapper(func):
        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            user_warned = not warn_user
            num_attempts = num_retries + 1  # +1 for the first attempt
            for attempt in range(1, num_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except RateLimitError:
                    if attempt == num_attempts:
                        raise

                    logger.debug(retry_limit_msg)
                    if not user_warned:
                        logger.double_check(api_key_error_msg)
                        user_warned = True

                except (APIError, Timeout) as e:
                    if (e.http_status not in [502, 429]) or (attempt == num_attempts):
                        raise

                backoff = backoff_base ** (attempt + 2)
                logger.debug(backoff_msg.format(backoff=backoff))
                time.sleep(backoff)
        return _wrapped
    return _wrapper


@meter_api
@retry_api()
def create_chat_completion(
    messages: List[MessageDict],
    *_,
    **kwargs,
) -> OpenAIObject:
    """Create a chat completion using the OpenAI API

    Args:
        messages: A list of messages to feed to the chatbot.
        kwargs: Other arguments to pass to the OpenAI API chat completion call.
    Returns:
        OpenAIObject: The ChatCompletion response from OpenAI

    """
    completion: OpenAIObject = openai.ChatCompletion.create(
        messages=messages,
        **kwargs,
    )
    if not hasattr(completion, "error"):
        logger.debug(f"Response: {completion}")
    return completion


@meter_api
@retry_api()
async def acreate_chat_completion(
    messages: List[MessageDict],
    *_,
    **kwargs,
) -> OpenAIObject:
    """Create a chat completion using the OpenAI API

    Args:
        messages: A list of messages to feed to the chatbot.
        kwargs: Other arguments to pass to the OpenAI API chat completion call.
    Returns:
        OpenAIObject: The ChatCompletion response from OpenAI

    """
    completion: OpenAIObject = await openai.ChatCompletion.acreate(
        messages=messages,
        **kwargs,
    )
    if not hasattr(completion, "error"):
        logger.debug(f"Response: {completion}")
    return completion


@meter_api
@retry_api()
def create_text_completion(
    prompt: str,
    *_,
    **kwargs,
) -> OpenAIObject:
    """Create a text completion using the OpenAI API

    Args:
        prompt: A text prompt to feed to the LLM
        kwargs: Other arguments to pass to the OpenAI API text completion call.
    Returns:
        OpenAIObject: The Completion response from OpenAI

    """
    return openai.Completion.create(
        prompt=prompt,
        **kwargs,
    )


@meter_api
@retry_api()
def create_embedding(
    input: str | TText | List[str] | List[TText],
    *_,
    **kwargs,
) -> OpenAIObject:
    """Create an embedding using the OpenAI API

    Args:
        input: The text to embed.
        kwargs: Other arguments to pass to the OpenAI API embedding call.
    Returns:
        OpenAIObject: The Embedding response from OpenAI

    """
    return openai.Embedding.create(
        input=input,
        **kwargs,
    )
