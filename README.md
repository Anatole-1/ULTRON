# Autonomous Pentest AI · IA de pentest autonome (ULTRON)

A local-LLM agent that runs a whole pentest on its own: recon → credential
attacks → vulnerability ID → exploitation → non-destructive post-exploitation →
written report, and can hand you an interactive Meterpreter root shell.
Not a chatbot — an **agent** that decides and acts in a loop until the report.

Un agent piloté par un LLM local qui mène seul tout un pentest : reconnaissance
→ attaque de credentials → identification de vulnérabilités → exploitation →
post-exploitation non destructive → rapport, et peut vous donner un shell root
Meterpreter interactif. Projet d'étude / portfolio.

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
(observer → raisonner → agir) : recon nmap → énumération par port → attaque de
credentials → (optionnel) exploitation → post-exploitation → rapport.

**Le LLM décide et analyse ; l'orchestrateur détient les faits.** Services
ouverts, résultats d'exploitation, credentials et collecte post-exploitation sont
construits à partir des sorties réelles des outils, jamais récités par le modèle.
La cible vient toujours de la ligne de commande (le modèle ne peut pas la changer).

- **Registre d'outils extensible** : ajouter un outil = une entrée + une fonction.
  Chaque outil peut porter un *hint* qui dit au modèle quand l'utiliser.
- **Attaque de credentials** (`hydra`) : brute-force des services d'auth ouverts
  (ftp, telnet…) avec une petite liste de mots de passe faibles ; les identifiants
  trouvés sont affichés en direct et listés dans le rapport.
- **Exploitation** (off par défaut, `--exploit`) : allow-list de modules Metasploit
  vérifiés, scope revérifié, `LHOST` auto, déclencheur par module.
- **Post-exploitation** : une fois root, collecte **en lecture seule** (identité,
  comptes, hashes, réseau). Jamais de persistance, destruction ou exfiltration.
- **Shell interactif** (`--shell`, ou à la demande en mode guidé) : après un
  exploit réussi, l'agent ouvre une session **Meterpreter** root et vous rend la
  main (`shell` pour un vrai shell où `cd` persiste).
- **Mode guidé** (`--guided`) : avant chaque action, l'agent montre ce qu'il veut
  faire et **vous décidez** — accepter, remplacer par votre action, ou arrêter.
- **Human-in-the-loop** : approbation avant exploit, indice si l'agent bloque.
  `-y` = autonome sans question. Non destructif et scope-gated de bout en bout.

## 🇬🇧 English

You launch the agent with a target; it drives itself in a ReAct loop
(observe → reason → act): nmap recon → per-port enumeration → credential attacks →
(optional) exploitation → post-exploitation → report.

**The LLM decides and analyses; the orchestrator owns the facts.** Open services,
exploitation results, credentials and post-exploitation collection are built from
real tool output, never recited by the model. The target always comes from the
command line (the model cannot change it).

- **Extensible tool registry**: adding a tool = one entry + one function. Each tool
  may carry a *hint* telling the model when to use it.
- **Credential attacks** (`hydra`): brute-force open auth services (ftp, telnet…)
  with a small list of common weak passwords; found logins are shown live and
  listed in the report.
- **Exploitation** (off by default, `--exploit`): allow-listed Metasploit modules,
  re-checked scope, auto-detected `LHOST`, per-module trigger.
- **Post-exploitation**: once root, **read-only** collection (identity, accounts,
  hashes, network). No persistence, destruction, or exfiltration.
- **Interactive shell** (`--shell`, or on demand in guided mode): after a
  successful exploit, the agent opens a **Meterpreter** root session and hands it
  to you (`shell` for a real shell where `cd` persists).
- **Guided mode** (`--guided`): before each action the agent shows what it wants
  to do and **you decide** — accept, replace with your own action, or stop.
- **Human-in-the-loop**: approval before exploits, a hint when the agent is stuck.
  `-y` runs unattended. Non-destructive and scope-gated throughout.

---

## Usage

```bash
pip install -r requirements.txt
cp scope.txt.example scope.txt          # edit: one IP or CIDR per line
ollama pull qwen3:8b                     # on the AI server

python3 agent.py <target-ip> --host http://<ai-server-ip>:11434                 # recon + credential attacks + report
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit       # + exploitation (asks first)
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit --shell   # + a Meterpreter root shell
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit --guided  # you steer every action
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit -y    # unattended, no prompts
```

`scope.txt` and generated reports stay local (git-ignored). Each run prints its
total time; adding a tool is a single entry in the `TOOLS` registry.

| Option · Flag        | Purpose · Rôle |
|----------------------|----------------|
| `target`             | Target IP (must be in scope) · IP cible (dans le scope). |
| `-H`, `--host`       | Ollama server URL (default `$OLLAMA_HOST`) · URL du serveur Ollama. |
| `-s`, `--scope`      | Scope file (default `scope.txt`) · fichier de scope. |
| `-m`, `--model`      | Model name (default `qwen3:8b`) · nom du modèle. |
| `--max-steps`        | Max reasoning steps (default 8) · étapes max. |
| `--exploit`          | Enable exploitation (off by default) · active l'exploitation. |
| `--shell`            | Hand a Meterpreter root shell after a successful exploit (interactive) · shell root après exploit. |
| `--guided`           | Validate or redirect each action before it runs (interactive) · valider/rediriger chaque action. |
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
| `agent.py`            | Orchestrator + ReAct loop, tool registry, guided mode, report builder. |
| `nmap_tool.py`        | Recon: scope-checked `nmap -sV` scan. |
| `enum_tool.py`        | Per-port enumeration: nmap vulnerability scripts. |
| `hydra_tool.py`       | Credential attack: scope-checked hydra with a small weak-password list. |
| `exploit_tool.py`     | Exploitation: scope-checked, allow-listed Metasploit modules. |
| `postexploit_tool.py` | Non-destructive post-exploitation + Meterpreter shell handoff. |
| `scope.py`            | The central safeguard: is a target in scope? |
| `scope.txt.example`   | Template scope file (copy to `scope.txt`). |
| `requirements.txt`    | Python dependencies (`requests`). |
| `BENCHMARK.md`        | Model comparison (why `qwen3:8b`). |

## Requirements · Prérequis

- Python 3 + `requests` · nmap + hydra + metasploit-framework (control host, preinstalled on Kali)
- A reachable Ollama server with the model pulled (`ollama pull qwen3:8b`)

## Roadmap

- [x] Hardened AI server (Ubuntu + GPU + Ollama), scope guardrail, agentic loop
- [x] Recon (nmap) + per-port enumeration + grounded report
- [x] Extensible tool registry with per-tool hints
- [x] Credential attacks (hydra) surfaced live and in the report
- [x] Exploitation: allow-listed modules, scope-checked, per-module triggers
- [x] Non-destructive post-exploitation (read-only impact)
- [x] Meterpreter root-shell handoff to the operator (`--shell`)
- [x] Guided mode: the operator accepts/redirects/stops each action (`--guided`)
- [x] Human-in-the-loop, run timing, analysis CVE-scrubbing
- [ ] More exploit modules and lab targets (DVWA, VulnHub, HTB)
- [ ] Larger wordlists for credential attacks on real targets

## Inspirations · License

Studied for inspiration: PentestGPT, Nebula, and agent frameworks (AutoGPT /
CrewAI) adapted for pentesting. Personal study project.
