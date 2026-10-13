# Autonomous Pentest AI

An autonomous penetration-testing agent driven by a local LLM.
Study project — designed to run exclusively in an isolated lab.

## Legal & ethical scope (read this first)

This is a learning project exploring the automation of penetration testing with
AI. It is meant to run **only** against:

- vulnerable virtual machines set up locally (isolated lab), or
- targets for which explicit written authorization has been obtained.

A scope guardrail sits at the core of the architecture: the agent refuses to act
on any target that is not listed in a declared rules-of-engagement file. This
check is hard-coded into the agent's tools.

Testing a system without authorization is illegal (in France, Article 323 of the
Penal Code). This repository must never be used against a third-party system.

## Goal

Build an autonomous agent (not a chatbot): you launch it with a target and a
scope, and it runs the whole mission on its own.

```bash
python agent.py --target 192.168.56.50 --scope scope.txt
```

It runs in an agentic loop (ReAct pattern):

```
observe -> reason -> act -> repeat
```

... until it produces a findings report.

Mission flow: reconnaissance -> vulnerability identification -> simple
exploitation attempts -> report.

## Architecture

The project deliberately separates the brain from the hands across two machines:

| Role | Machine | Function |
|------|---------|----------|
| Brain | AI server (headless) | Runs the LLM. Takes a state, returns the next action to perform. Never touches the target. |
| Hands | Control host (Kali Linux) | Python orchestrator + pentest tools. Checks the scope, runs the tools, sends results back to the brain. |

```
   [ Brain: LLM ]  <--- state / decisions --->  [ Hands: orchestrator + tools ]
       (Ollama)                                     (Python, nmap, ...)
                                                             |
                                                        scope check
                                                             |
                                                         [ target ]  (isolated lab)
```

## Tech stack

- Language: Python
- Local LLM: [Ollama](https://ollama.com/) — model tested: `qwen2.5:7b`
- AI server: Ubuntu Server 24.04 LTS, NVIDIA RTX 4060 GPU (8 GB VRAM)
- Pentest tools: nmap (more added progressively)

Starting fully local (free, self-contained), with a planned comparison between
model sizes (local 8B vs. larger cloud models).

## Roadmap

- [x] AI server up and running (Ubuntu + GPU driver + Ollama)
- [x] First model downloaded and tested (`qwen2.5:7b`)
- [ ] Expose the LLM API on the local network (remote control)
- [ ] Harden the server (SSH key, firewall, fail2ban)
- [ ] Minimal script: orchestrator <-> LLM API dialogue
- [ ] First tool wired in: run `nmap` against an in-scope target
- [ ] Full agentic loop with scope enforcement
- [ ] Findings report generation
- [ ] Vulnerable-VM lab for training

## Inspirations

Open-source projects studied for inspiration: PentestGPT, Nebula, and agent
frameworks (AutoGPT / CrewAI) adapted for pentesting.

## License

Personal study project. (License to be defined.)
