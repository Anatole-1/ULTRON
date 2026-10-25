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

## How it works

Launch the agent against an authorized target. A local LLM decides each action,
an orchestrator executes it through scope-enforced tools, and the loop repeats
until a findings report.

```bash
python3 agent.py 192.168.56.50
```

ReAct loop: observe -> reason -> act -> repeat.

## Architecture

The project separates the brain from the hands across two machines:

| Role | Machine | Function |
|------|---------|----------|
| Brain | AI server (headless) | Runs the LLM via Ollama. Returns the next action. Never touches the target. |
| Hands | Control host (Kali) | Python orchestrator + tools. Checks scope, runs tools, returns results to the brain. |

The server URL is never hard-coded: it is read from `--host` or the
`OLLAMA_HOST` environment variable.

## Requirements

- Python 3
- `nmap` installed and on PATH
- A reachable Ollama server running a model (default `qwen2.5:7b`)

## Installation

```bash
git clone https://github.com/Anatole-1/ia-pentest-autonome.git
cd ia-pentest-autonome
pip install -r requirements.txt
cp scope.txt.example scope.txt      # then edit scope.txt with your authorized targets
```

## Usage

```bash
export OLLAMA_HOST="http://<your-ollama-host>:11434"

python3 agent.py <target-ip>
python3 agent.py <target-ip> --scope scope.txt --model qwen2.5:7b --max-steps 6
python3 agent.py --help
```

The target must be listed in the scope file, otherwise the scan is refused.

## Repository layout

| File | Purpose |
|------|---------|
| `agent.py` | CLI + ReAct loop: the LLM decides, the orchestrator executes with scope enforcement. |
| `nmap_tool.py` | nmap reconnaissance tool; refuses out-of-scope targets. |
| `scope.py` | Scope verification (single IP and CIDR ranges). |
| `scope.txt.example` | Rules-of-engagement template; copy to `scope.txt`. |
| `requirements.txt` | Python dependencies. |

> `scope.txt` is gitignored — it holds real engagement targets and stays local.

## Tech stack

- Language: Python (argparse CLI)
- Local LLM: [Ollama](https://ollama.com/) — model tested: `qwen2.5:7b`
- Pentest tools: nmap (more added progressively)

Starting fully local, with a planned comparison between model sizes.

## Roadmap

- [x] AI server up and running (Ubuntu + GPU driver + Ollama)
- [x] Expose the LLM API on the LAN; harden the server (SSH key, firewall, fail2ban)
- [x] Remote access over a private mesh (Tailscale)
- [x] Scope guardrail: refuse any out-of-scope target
- [x] nmap reconnaissance tool
- [x] Autonomous ReAct loop (LLM drives) with a structured report
- [ ] Additional tools (targeted service enumeration)
- [ ] Findings report written to a dated file
- [ ] Broader lab targets (DVWA, VulnHub, TryHackMe/HTB)

## Inspirations

Open-source projects studied for inspiration: PentestGPT, Nebula, and agent
frameworks (AutoGPT / CrewAI) adapted for pentesting.

## License

Personal study project.
