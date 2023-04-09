import random
from colorama import Fore, Style
import time
import auto_gpt.speak


def print_to_console(
    title,
    title_color,
    content,
    speak_text=False,
    min_typing_speed=0.05,
    max_typing_speed=0.01,
):
    if speak_text:
        speak.say_text(f"{title}. {content}")
    print(title_color + title + " " + Style.RESET_ALL, end="")
    if content:
        if isinstance(content, list):
            content = " ".join(content)
        words = content.split()
        for i, word in enumerate(words):
            print(word, end="", flush=True)
            if i < len(words) - 1:
                print(" ", end="", flush=True)
            typing_speed = random.uniform(min_typing_speed, max_typing_speed)
            time.sleep(typing_speed)
            # type faster after each word
            min_typing_speed = min_typing_speed * 0.95
            max_typing_speed = max_typing_speed * 0.95
    print()


def print_assistant_thoughts(ai_name, thought, speak_text=False):
    print(Fore.YELLOW + f"--- {ai_name.upper()} ---\n" + Style.RESET_ALL, end="")
    print_to_console("THOUGHTS:", Fore.YELLOW, thought.text)
    print_to_console("REASONING:", Fore.YELLOW, thought.reasoning)
    # TODO: Make thought a list
    print_to_console("PLAN:", Fore.YELLOW, "")
    for plan in thought.plan:
        print_to_console("- ", Fore.GREEN, plan)
    print_to_console("CRITICISM:", Fore.YELLOW, thought.criticism)
    print_to_console("SPEAK:", Fore.YELLOW, thought.speak)
    # Speak the assistant's thoughts
    if speak_text:
        speak.say_text(thought.speak)
