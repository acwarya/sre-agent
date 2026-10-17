"""Minimal local SRE agent: an LLM (via Ollama) that calls read-only tools
to inspect a Windows machine, then summarizes what it finds."""

import argparse
import shutil
import subprocess

import ollama

DEFAULT_MODEL = "llama3.1"
DEFAULT_QUESTION = "Is my disk healthy and is the Spooler service running?"
MAX_STEPS = 6  # safety cap so the agent loop can never run forever


# ----------------------------- Tools (read-only) -----------------------------

def check_disk(drive: str = "C") -> str:
    """Show disk usage for a drive.

    Args:
        drive: drive letter, e.g. C or D. Defaults to C.
    """
    letter = drive.strip().rstrip(":\\/").upper() or "C"
    try:
        total, used, free = shutil.disk_usage(f"{letter}:\\")
    except (FileNotFoundError, OSError):
        return f"Drive {letter}: not found"
    gb = 1024 ** 3
    return (
        f"{letter}: total {total / gb:.1f} GB, "
        f"used {used / gb:.1f} GB, free {free / gb:.1f} GB"
    )


def check_service(name: str) -> str:
    """Check the status of a Windows service.

    Args:
        name: service name, e.g. Spooler or docker
    """
    # The name is interpolated into a PowerShell command, so validate it first.
    if not name.replace("_", "").replace("-", "").replace(".", "").isalnum():
        return "Invalid service name"
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue).Status",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() or f"Service '{name}' not found"


TOOLS = {"check_disk": check_disk, "check_service": check_service}


# ------------------------------- Agent loop ----------------------------------

def run_agent(question: str, model: str) -> None:
    messages = [{"role": "user", "content": question}]

    for _ in range(MAX_STEPS):
        response = ollama.chat(model=model, messages=messages, tools=list(TOOLS.values()))
        messages.append(response.message)

        # No tool calls means the model has produced its final answer.
        if not response.message.tool_calls:
            print("\nAnswer:\n" + (response.message.content or ""))
            return

        for call in response.message.tool_calls:
            name, args = call.function.name, call.function.arguments
            print(f"[tool call]   {name} {args}")
            try:
                result = TOOLS[name](**args)
            except KeyError:
                result = f"Error: unknown tool '{name}'. Available: {list(TOOLS)}"
            except TypeError as exc:
                result = f"Error: bad arguments for {name}: {exc}"
            print(f"[tool result] {result}")
            messages.append({"role": "tool", "tool_name": name, "content": result})

    print("Stopped: reached the maximum number of steps without a final answer.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local SRE agent powered by Ollama.")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION, help="what to ask the agent")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()
    run_agent(args.question, args.model)
