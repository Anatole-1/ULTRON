# Autonomous Pentest AI

An autonomous penetration-testing agent driven by a local LLM. You give it a
single target; it runs the whole mission on its own: reconnaissance,
vulnerability identification, exploitation, and a written report.

Study / portfolio project — designed to run **only** in an isolated lab.

## ⚠️ Legal & ethical scope (read this first)

This project **exploits** real vulnerabilities and can open a root shell on its
target. Run it **only** against:

- vulnerable virtual machines you own, on an isolated network, or
- systems for which you hold explicit written authorization.

Using it against any other system is illegal. In France, unauthorized access to
a computer system is punished under articles 323-1 et seq. of the Code pénal;
most countries have equivalent laws.

A scope guardrail sits at the core of the architecture: every tool refuses to
act on a target not listed in the declared rules-of-engagement file
(scope.txt). This check is hard-coded into each tool, recon and exploitation
alike.

## How it works

You launch the agent with a target; it drives itself in a ReAct loop
(observe -> reason -> act) until it produces a report.

    export OLLAMA_HOST="http://<ai-server-ip>:11434"
    python3 agent.py 192.168.56.50               # recon + report only
    python3 agent.py 192.168.56.50 --exploit     # recon, then exploitation

Mission flow: nmap recon -> per-port enumeration -> (optional) exploitation -> report

The LLM only decides and analyses; the orchestrator owns the facts. The open
services and exploitation results in the report are built from real tool output,
never from the model, so the report cannot hallucinate a port or a shell.

## Exploitation

Exploitation is **off by default** and only enabled with --exploit. It is
deliberately constrained:

- **Allow-list only.** The agent runs a small set of vetted Metasploit modules,
  never an arbitrary one. Current list:
  - vsftpd_234_backdoor  -- vsftpd 2.3.4 FTP backdoor
  - samba_usermap_script -- Samba 3.x usermap_script RCE
- **Scope-checked.** Every exploit re-verifies the target is in scope.txt.
- **Portable.** The reverse-shell LHOST is auto-detected from the route to the
  target, so it works on any network without editing the code.
- **Adaptive.** If one module yields no session, the agent falls back to another
  module matching an open service before giving up.

Adding a module is a single entry in exploit_tool.py; nothing else changes.

## Architecture

The project separates the brain from the hands across two machines:

| Role  | Machine              | Function |
|-------|----------------------|----------|
| Brain | AI server (headless) | Runs the LLM. Takes a state, returns the next action. Never touches the target. |
| Hands | Control host (Kali)  | Python orchestrator + pentest tools. Checks scope, runs the tools, feeds results back to the brain. |

The server address is never hard-coded: the orchestrator reads it from the
OLLAMA_HOST environment variable (or --host), so no infrastructure detail lives
in the repository.

## Tech stack

- Language: Python 3
- Local LLM: Ollama -- model tested: qwen2.5:7b
- Recon: nmap
- Exploitation: Metasploit Framework (msfconsole)
- AI server: Ubuntu Server 24.04 LTS, NVIDIA RTX 4060 (8 GB VRAM)

## Requirements

- Python 3 with requests (pip install -r requirements.txt)
- nmap and metasploit-framework on the control host (preinstalled on Kali)
- A reachable Ollama server with the model pulled (ollama pull qwen2.5:7b)

## Setup

    pip install -r requirements.txt
    cp scope.txt.example scope.txt     # then edit: one IP or CIDR per line
    export OLLAMA_HOST="http://<ai-server-ip>:11434"
    python3 agent.py <target-ip> --exploit

scope.txt and generated reports stay local (git-ignored): they describe your
own lab.

## Repository layout

| File | Purpose |
|------|---------|
| agent.py           | Orchestrator + ReAct loop: drives the mission and writes the report. |
| nmap_tool.py       | Reconnaissance: scope-checked nmap -sV service scan. |
| enum_tool.py       | Per-port enumeration: scope-checked nmap vulnerability scripts. |
| exploit_tool.py    | Exploitation: scope-checked, allow-listed Metasploit modules. |
| scope.py           | The central safeguard: decides whether a target is in scope. |
| test_connection.py | Minimal connectivity test: one prompt to the LLM, prints the reply. |
| scope.txt.example  | Template rules-of-engagement file (copy to scope.txt). |
| requirements.txt   | Python dependencies. |

## Roadmap

- [x] AI server up and running (Ubuntu + GPU driver + Ollama)
- [x] Model downloaded and tested (qwen2.5:7b)
- [x] Expose the LLM API on the private network
- [x] Harden the server (SSH key, firewall, fail2ban)
- [x] Orchestrator <-> LLM API dialogue
- [x] Scope guardrail: refuse any out-of-scope target
- [x] Recon tool: nmap against an in-scope target
- [x] Full agentic loop with scope enforcement
- [x] Findings report generation
- [x] Vulnerable-VM lab for testing
- [x] Exploitation: allow-listed modules, scope-checked, adaptive fallback
- [ ] Tool registry to make adding tools trivial
- [ ] Human-in-the-loop escalation after repeated failures
- [ ] More exploit modules
- [ ] Persistent Metasploit instance (msfrpcd) to cut startup latency
- [ ] Benchmark: local 7B vs. larger cloud models

## Inspirations

Open-source projects studied for inspiration: PentestGPT, Nebula, and agent
frameworks (AutoGPT / CrewAI) adapted for pentesting.

## License

Personal study project.
