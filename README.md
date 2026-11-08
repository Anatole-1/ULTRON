# Autonomous Pentest AI · IA de pentest autonome

A local-LLM agent that runs a whole pentest on its own: recon → vulnerability
ID → exploitation → non-destructive post-exploitation → written report, and can
hand you an interactive root shell on the target.
Not a chatbot — an **agent** that decides and acts in a loop until the report.

Un agent piloté par un LLM local qui mène seul tout un pentest : reconnaissance
→ identification de vulnérabilités → exploitation → post-exploitation non
destructive → rapport, et peut vous donner un shell root interactif sur la cible.
Projet d'étude / portfolio.

> ⚠️ **Lab use only.** Runs real exploits and can open a root shell. Use it only
> on VMs you own (isolated network) or systems you have written authorization for.
> Unauthorized use is illegal. A hard-coded **scope guardrail** makes every tool
> refuse any target absent from `scope.txt`.
>
> ⚠️ **Labo uniquement.** Exécute de vrais exploits et peut ouvrir un shell root.
> À utiliser seulement sur des VM que vous possédez (réseau isolé) ou avec
> autorisation écrite. Tout autre usage est illégal. Un **garde-fou de scope**
> codé en dur fait refuser à chaque outil toute cible absente de `scope.txt`.

---

## 🇫🇷 Français

On lance l'agent avec une cible ; il se pilote dans une boucle ReAct
(observer → raisonner → agir) : recon nmap → énumération par port →
(optionnel) exploitation → post-exploitation → rapport.

**Le LLM décide et analyse ; l'orchestrateur détient les faits.** Services
ouverts, résultats d'exploitation et collecte post-exploitation sont construits
à partir des sorties réelles des outils, jamais récités par le modèle — le
rapport ne peut pas halluciner un port ou un shell. Les CVE non vus dans une
observation sont retirés de l'analyse.

- **Exploitation** (off par défaut, flag `--exploit`) : allow-list de modules
  Metasploit vérifiés, scope revérifié, `LHOST` auto-détecté, bascule adaptative
  entre modules si pas de session. Chaque module porte un *déclencheur* (le
  service nmap attendu) qui aide le modèle à tirer le bon exploit tout de suite.
- **Post-exploitation** : une fois root, collecte **en lecture seule** (identité,
  comptes, hashes, réseau) pour démontrer l'impact. Jamais de persistance,
  destruction ou exfiltration.
- **Shell interactif** (flag `--shell`, interactif uniquement) : après un exploit
  réussi, l'agent ouvre une vraie session msfconsole root sur la cible et vous
  rend la main — vous tapez directement dedans. Scope-gated.
- **Human-in-the-loop** : en interactif, l'agent demande avant chaque exploit
  (`y`/`N`/`a` = oui à tout) et réclame un indice s'il bloque. `-y` = sans
  question (autonome). Non destructif et scope-gated de bout en bout.

## 🇬🇧 English

You launch the agent with a target; it drives itself in a ReAct loop
(observe → reason → act): nmap recon → per-port enumeration → (optional)
exploitation → post-exploitation → report.

**The LLM decides and analyses; the orchestrator owns the facts.** Open
services, exploitation results, and post-exploitation collection are built from
real tool output, never recited by the model — the report cannot hallucinate a
port or a shell. CVEs never seen in an observation are stripped from the analysis.

- **Exploitation** (off by default, `--exploit`): allow-listed Metasploit
  modules, re-checked scope, auto-detected `LHOST`, adaptive fallback between
  modules when no session opens. Each module carries a *trigger* (the expected
  nmap service) that helps the model fire the right exploit immediately.
- **Post-exploitation**: once root, **read-only** collection (identity, accounts,
  hashes, network) to demonstrate impact. No persistence, destruction, or exfiltration.
- **Interactive shell** (`--shell`, interactive only): after a successful exploit,
  the agent opens a real msfconsole root session on the target and hands it to
  you — you type directly in it. Scope-gated.
- **Human-in-the-loop**: when interactive, the agent asks before each exploit
  (`y`/`N`/`a` = yes-to-all) and requests a hint when stuck. `-y` runs unattended.
  Non-destructive and scope-gated throughout.

---

## Usage

```bash
pip install -r requirements.txt
cp scope.txt.example scope.txt          # edit: one IP or CIDR per line
ollama pull qwen3:8b                     # on the AI server

python3 agent.py <target-ip> --host http://<ai-server-ip>:11434               # recon + report
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit     # + exploitation (asks first)
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit --shell  # + hands you a root shell
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit -y   # unattended, no prompts
```

`scope.txt` and generated reports stay local (git-ignored). Each run prints its
total time; adding a recon tool is a single entry in the `TOOLS` registry.

| Option · Flag        | Purpose · Rôle |
|----------------------|----------------|
| `target`             | Target IP (must be in scope) · IP cible (dans le scope). |
| `-H`, `--host`       | Ollama server URL (default `$OLLAMA_HOST`) · URL du serveur Ollama. |
| `-s`, `--scope`      | Scope file (default `scope.txt`) · fichier de scope. |
| `-m`, `--model`      | Model name (default `qwen3:8b`) · nom du modèle. |
| `--max-steps`        | Max reasoning steps (default 8) · étapes max. |
| `--exploit`          | Enable exploitation (off by default) · active l'exploitation. |
| `--shell`            | Hand an interactive root shell to the operator after a successful exploit (interactive only) · donne un shell root interactif après un exploit réussi. |
| `-y`, `--yes`        | Auto-approve, no prompts · tout approuver, sans question. |
| `--think`            | Enable model reasoning (slower) · active le raisonnement (plus lent). |

## Architecture

| Role · Rôle | Machine | Function · Fonction |
|-------------|---------|---------------------|
| Brain · Cerveau | AI server (headless) | Runs the LLM. Returns the next action. Never touches the target. · Exécute le LLM, renvoie l'action. Ne touche jamais la cible. |
| Hands · Mains   | Control host (Kali)  | Python orchestrator + tools. Checks scope, runs tools, feeds results back. · Orchestrateur + outils, vérifie le scope, exécute. |

The server address is never hard-coded (read from `--host` / `OLLAMA_HOST`).

## Repository layout · Structure

| File | Purpose · Rôle |
|------|----------------|
| `agent.py`            | Orchestrator + ReAct loop, tool registry, report builder. |
| `nmap_tool.py`        | Recon: scope-checked `nmap -sV` scan. |
| `enum_tool.py`        | Per-port enumeration: nmap vulnerability scripts. |
| `exploit_tool.py`     | Exploitation: scope-checked, allow-listed Metasploit modules. |
| `postexploit_tool.py` | Non-destructive post-exploitation + interactive shell handoff. |
| `scope.py`            | The central safeguard: is a target in scope? |
| `scope.txt.example`   | Template scope file (copy to `scope.txt`). |
| `requirements.txt`    | Python dependencies (`requests`). |
| `BENCHMARK.md`        | Model comparison (why `qwen3:8b`). |

## Requirements · Prérequis

- Python 3 + `requests` · nmap + metasploit-framework (control host, preinstalled on Kali)
- A reachable Ollama server with the model pulled (`ollama pull qwen3:8b`)

## Roadmap

- [x] Hardened AI server (Ubuntu + GPU + Ollama), scope guardrail, agentic loop
- [x] Recon (nmap) + per-port enumeration + grounded report
- [x] Exploitation: allow-listed modules, scope-checked, adaptive fallback
- [x] Non-destructive post-exploitation (read-only impact)
- [x] Tool registry · multi-service recon before concluding
- [x] Human-in-the-loop: approval gate + stuck detection
- [x] Model benchmark (qwen3:8b), analysis CVE-scrubbing, run timing
- [x] Interactive root-shell handoff to the operator (`--shell`, via msfconsole)
- [ ] Fully automatic TTY upgrade for the handed-off shell (pwncat / meterpreter)
- [ ] More exploit modules and lab targets (DVWA, VulnHub, HTB)

## Inspirations · License

Studied for inspiration: PentestGPT, Nebula, and agent frameworks (AutoGPT /
CrewAI) adapted for pentesting. Personal study project.
