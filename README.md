# SRE Agent: a minimal local agentic AI

A small, free, fully local AI agent that inspects a Windows machine the way an SRE would. A local LLM (via [Ollama](https://ollama.com)) decides which read-only tools to call, your code executes them, and the model summarizes the results in plain English. No API keys, no cloud costs.

## How it works

```
 question ──► LLM ──► "call check_disk" ──► your Python tool runs
                ▲                                   │
                └────────── tool result ◄───────────┘
                (repeat until the LLM answers in plain text)
```

The model never runs anything itself. It only *requests* a tool call; the script executes it and feeds the result back. The loop is capped at 6 steps.

### Tools

| Tool | What it does |
|---|---|
| `check_disk(drive)` | Reports total, used, and free space for a drive letter (default `C`) |
| `check_service(name)` | Reports whether a Windows service (e.g. `Spooler`) is running |

Both tools are **read-only** by design.

## Requirements

- Windows 10/11
- Python 3.10+ (check "Add python.exe to PATH" during install)
- [Ollama](https://ollama.com/download)
- About 8 GB RAM (16 GB recommended) for `llama3.1`. For lower-end machines use `qwen2.5:3b`.

## Setup

```powershell
# 1. Clone the repo
git clone https://github.com/acwarya/sre-agent.git
cd sre-agent

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download a model (one-time, ~5 GB)
ollama pull llama3.1
```

If PowerShell blocks the activation script, run this once and retry step 2:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Run

```powershell
# Default question
python agent.py

# Ask your own
python agent.py "How much free space is on drive C?"
python agent.py "Is the Windows Update service running?"

# Use a different model
python agent.py --model qwen2.5:3b "Is the Spooler service running?"
```

Example output:

```
[tool call]   check_disk {'drive': 'C'}
[tool result] C: total 475.9 GB, used 210.3 GB, free 265.6 GB
[tool call]   check_service {'name': 'Spooler'}
[tool result] Running

Answer:
Your C: drive has about 265 GB free (roughly 56% of capacity) and the Print Spooler service is running.
```

## Testing

**Test the tools without the AI:**

```powershell
python -c "from agent import check_disk, check_service; print(check_disk()); print(check_service('Spooler')); print(check_service('FakeService'))"
```

**Cross-check against Windows:** compare against `Get-Service Spooler` in PowerShell and the drive properties in File Explorer.

**Try different questions** and watch the `[tool call]` lines to see whether the model picks the right tool:

| Question | Expected behavior |
|---|---|
| "How much free space do I have?" | calls only `check_disk` |
| "Is the Windows Update service running?" | calls `check_service` with `wuauserv` |
| "What's the capital of France?" | calls no tools |

## Troubleshooting

| Problem | Fix |
|---|---|
| `model 'llama3.1' not found (404)` | Run `ollama pull llama3.1`, or run `ollama list` and pass the exact name with `--model` |
| Connection refused / cannot connect | Ollama isn't running. Start it from the Start menu or run `ollama serve` |
| `ollama` not recognized | Close and reopen PowerShell after installing Ollama |
| Slow or out-of-memory | Use a smaller model: `ollama pull qwen2.5:3b` |
| Model ignores tools or invents values | Common with very small models. Use `llama3.1` and compare the answer to the `[tool result]` lines |

## Design notes

- **Read-only tools:** safe to experiment with. Add confirmation prompts before ever adding tools that change system state.
- **Input validation:** service names are validated before being passed to PowerShell.
- **Error feedback:** bad tool names or arguments are returned to the model as an error message so it can self-correct, instead of crashing.
- **Step cap:** the loop stops after 6 rounds.

## Ideas for extending

- Read Windows Event Log errors (`Get-WinEvent`)
- List top CPU/memory processes
- Query a Prometheus endpoint for metrics
- Build a full on-call triage agent that correlates logs and metrics and suggests likely causes
- Add unit tests for the tools

## License

MIT
