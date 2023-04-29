"""Fix and parse JSON strings."""
from __future__ import annotations

import contextlib
import json
from typing import Any, Dict, Union

from colorama import Fore
from regex import regex

from autogpt.config import Config
from autogpt.json_fixes.auto_fix import fix_json
from autogpt.json_fixes.bracket_termination import balance_braces
from autogpt.json_fixes.escaping import fix_invalid_escape
from autogpt.json_fixes.missing_quotes import add_quotes_to_property_names
from autogpt.logs import logger
from autogpt.speech import say_text

CFG = Config()

JSON_SCHEMA = """
{
    "command": {
        "name": "command name",
        "args": {
            "arg name": "value"
        }
    },
    "thoughts":
    {
        "text": "thought",
        "reasoning": "reasoning",
        "plan": "- short bulleted\n- list that conveys\n- long-term plan",
        "criticism": "constructive self-criticism",
        "speak": "thoughts summary to say to user"
    }
}
"""


def correct_json(json_to_load: str) -> str:
    """
    Correct common JSON errors.
    Args:
        json_to_load (str): The JSON string.
    """

    try:
        if CFG.debug_mode:
            print("json", json_to_load)
        json.loads(json_to_load)
        return json_to_load
    except json.JSONDecodeError as e:
        if CFG.debug_mode:
            print("json loads error", e)
        error_message = str(e)
        if error_message.startswith("Invalid \\escape"):
            json_to_load = fix_invalid_escape(json_to_load, error_message)
        if error_message.startswith(
            "Expecting property name enclosed in double quotes"
        ):
            json_to_load = add_quotes_to_property_names(json_to_load)
            try:
                json.loads(json_to_load)
                return json_to_load
            except json.JSONDecodeError as e:
                if CFG.debug_mode:
                    print("json loads error - add quotes", e)
                error_message = str(e)
        if balanced_str := balance_braces(json_to_load):
            return balanced_str
    return json_to_load


async def fix_and_parse_json(
    json_to_load: str, try_to_fix_with_gpt: bool = True
) -> Dict[Any, Any]:
    """Fix and parse JSON string

    Args:
        json_to_load (str): The JSON string.
        try_to_fix_with_gpt (bool, optional): Try to fix the JSON with GPT.
            Defaults to True.

    Returns:
        str or dict[Any, Any]: The parsed JSON.
    """

    with contextlib.suppress(json.JSONDecodeError):
        json_to_load = json_to_load.replace("\t", "")
        return json.loads(json_to_load)

    with contextlib.suppress(json.JSONDecodeError):
        json_to_load = correct_json(json_to_load)
        return json.loads(json_to_load)
    # Let's do something manually:
    # sometimes GPT responds with something BEFORE the braces:
    # "I'm sorry, I don't understand. Please try again."
    # {"text": "I'm sorry, I don't understand. Please try again.",
    #  "confidence": 0.0}
    # So let's try to find the first brace and then parse the rest
    #  of the string
    try:
        brace_index = json_to_load.index("{")
        maybe_fixed_json = json_to_load[brace_index:]
        last_brace_index = maybe_fixed_json.rindex("}")
        maybe_fixed_json = maybe_fixed_json[: last_brace_index + 1]
        return json.loads(maybe_fixed_json)
    except (json.JSONDecodeError, ValueError) as e:
        return await try_ai_fix(try_to_fix_with_gpt, e, json_to_load)


async def try_ai_fix(
    try_to_fix_with_gpt: bool, exception: Exception, json_to_load: str
) -> Dict[Any, Any]:
    """Try to fix the JSON with the AI

    Args:
        try_to_fix_with_gpt (bool): Whether to try to fix the JSON with the AI.
        exception (Exception): The exception that was raised.
        json_to_load (str): The JSON string to load.

    Raises:
        exception: If try_to_fix_with_gpt is False.

    Returns:
        str or dict[Any, Any]: The JSON string or dictionary.
    """
    if not try_to_fix_with_gpt:
        raise exception
    if CFG.debug_mode:
        logger.warn(
            "Warning: Failed to parse AI output, attempting to fix."
            "\n If you see this warning frequently, it's likely that"
            " your prompt is confusing the AI. Try changing it up"
            " slightly."
        )
    # Now try to fix this up using the ai_functions
    ai_fixed_json = await fix_json(json_to_load, JSON_SCHEMA)

    if ai_fixed_json != "failed":
        return json.loads(ai_fixed_json)
    # This allows the AI to react to the error message,
    #   which usually results in it correcting its ways.
    # logger.error("Failed to fix AI output, telling the AI.")
    return {}


def attempt_to_fix_json_by_finding_outermost_brackets(json_string: str):
    if CFG.speak_mode and CFG.debug_mode:
        say_text(
            "I have received an invalid JSON response from the OpenAI API. "
            "Trying to fix it now."
        )
        logger.error("Attempting to fix JSON by finding outermost brackets\n")

    try:
        json_pattern = regex.compile(r"\{(?:[^{}]|(?R))*\}")
        json_match = json_pattern.search(json_string)

        if json_match:
            # Extract the valid JSON object from the string
            json_string = json_match.group(0)
            logger.typewriter_log(
                title="Apparently json was fixed.", title_color=Fore.GREEN
            )
            if CFG.speak_mode and CFG.debug_mode:
                say_text("Apparently json was fixed.")
        else:
            return {}

    except (json.JSONDecodeError, ValueError):
        if CFG.debug_mode:
            logger.error(f"Error: Invalid JSON: {json_string}\n")
        if CFG.speak_mode:
            say_text("Didn't work. I will have to ignore this response then.")
        logger.error("Error: Invalid JSON, setting it to empty JSON now.\n")
        json_string = {}

    return fix_and_parse_json(json_string)
