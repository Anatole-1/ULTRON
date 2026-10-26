# Autonomous Pentest AI

An autonomous penetration-testing agent driven by a local LLM.
Study project — designed to run exclusively in an isolated lab.

## Legal & ethical scope (read this first)

This is a learning project exploring the automation of penetration testing with
AI. It is meant to run **only** against:

- vulnerable virtual machines set up locally (isolated lab), or
- targets for which explicit written authorization has been obtained.

A scope guardrail is hard-coded into the tools: any target not listed in the
declared rules-of-engagement file is refused, even in autonomous mode.

## Quickstart

```bash
# 1. Get the code and install dependencies
git clone https://github.com/Anatole-1/ia-pentest-autonome.git
cd ia-pentest-autonome
pip install -r requirements.txt

# 2. Declare your authorized target(s)
cp scope.txt.example scope.txt
# edit scope.txt: one allowed IP or CIDR range per line

# 3. Run a mission (point --host at your Ollama server)
python3 agent.py <target-ip> --host http://<ollama-server>:11434
```

On startup the agent checks its prerequisites (nmap, the scope file, and that the
Ollama server is reachable) and prints a clear message if something is missing.

## How it works

A local LLM decides each action, an orchestrator runs it through scope-enforced
tools, and the loop repeats until a findings report.

ReAct loop: observe -> reason -> act -> repeat.

## Architecture

| Role | Machine | Function |
|------|---------|----------|
| Brain | AI server (headless) | Runs the LLM via Ollama. Returns the next action. Never touches the target. |
| Hands | Control host (Kali) | Python orchestrator + tools. Checks scope, runs tools, returns results to the brain. |

The server URL is read from `--host` or the `OLLAMA_HOST` environment variable,
so no infrastructure detail is hard-coded.

## Requirements

- Python 3
- `nmap` installed and on PATH
- A reachable Ollama server running a model (default `qwen2.5:7b`)

## Usage

```bash
python3 agent.py <target-ip> --host http://<ollama-server>:11434
python3 agent.py <target-ip> --scope scope.txt --model qwen2.5:7b --max-steps 6
python3 agent.py --help
```

The target must be listed in the scope file, otherwise the scan is refused.
Instead of `--host` you can export `OLLAMA_HOST` once per shell.

## Repository layout

| File | Purpose |
|------|---------|
| `agent.py` | CLI + ReAct loop: the LLM decides, the orchestrator executes with scope enforcement. |
| `nmap_tool.py` | nmap reconnaissance tool; refuses out-of-scope targets. |
| `scope.py` | Scope verification (single IP and CIDR ranges). |
| `scope.txt.example` | Rules-of-engagement template; copy to `scope.txt`. |
| `requirements.txt` | Python dependencies. |
| `BENCHMARK.md` | Model comparison and the chosen model. |

> `scope.txt` is gitignored — it holds real engagement targets and stays local.

## Tech stack

- Language: Python (argparse CLI)
- Local LLM: [Ollama](https://ollama.com/) — model used: `qwen2.5:7b`
- Pentest tools: nmap (more added progressively)

## Roadmap

- [x] AI server up and running (Ubuntu + GPU driver + Ollama)
- [x] Expose the LLM API on the LAN; harden the server (SSH key, firewall, fail2ban)
- [x] Remote access over a private mesh (Tailscale)
- [x] Scope guardrail: refuse any out-of-scope target
- [x] nmap reconnaissance tool
- [x] Autonomous ReAct loop (LLM drives) with a structured report
- [x] Model benchmark
- [x] Startup preflight checks
- [ ] Additional tools (targeted service enumeration)
- [ ] Findings report written to a dated file
- [ ] Broader lab targets (DVWA, VulnHub, TryHackMe/HTB)

## Inspirations

Open-source projects studied for inspiration: PentestGPT, Nebula, and agent
frameworks (AutoGPT / CrewAI) adapted for pentesting.

## License

Personal study project.
