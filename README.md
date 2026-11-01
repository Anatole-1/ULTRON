# Autonomous Pentest AI · IA de pentest autonome

An autonomous penetration-testing agent driven by a local LLM. You give it a
single target; it runs the whole mission on its own — reconnaissance,
vulnerability identification, exploitation, non-destructive post-exploitation,
and a written report.

Study / portfolio project — designed to run **only** in an isolated lab.

**🇫🇷 [Lire en français](#-français) · 🇬🇧 [Read in English](#-english)**

---

## 🇫🇷 Français

Un agent de test d'intrusion **autonome**, piloté par un LLM exécuté en local.
On lui donne une cible ; il mène seul toute la mission : reconnaissance,
identification des vulnérabilités, exploitation, post-exploitation non
destructive, puis un rapport écrit.

Ce n'est pas un chatbot : c'est un **agent** qui décide et agit dans une boucle,
jusqu'au rapport final.

Projet d'étude / portfolio — conçu pour tourner **uniquement** en laboratoire
isolé.

### ⚠️ Cadre légal et éthique (à lire en premier)

Ce projet **exploite** de vraies vulnérabilités et peut ouvrir un shell root sur
sa cible. À n'utiliser **que** contre :

- des machines virtuelles vulnérables que vous possédez, sur un réseau isolé, ou
- des systèmes pour lesquels vous disposez d'une **autorisation écrite explicite**.

L'utiliser contre tout autre système est illégal. En France, l'accès frauduleux
à un système de traitement automatisé de données est puni par les articles
323-1 et suivants du Code pénal ; la plupart des pays ont des lois équivalentes.

Un **garde-fou de scope** est au cœur de l'architecture : chaque outil refuse
d'agir sur une cible absente du fichier de périmètre déclaré (`scope.txt`). Cette
vérification est codée en dur dans tous les outils — reconnaissance comme
exploitation.

### Comment ça marche

On lance l'agent avec une cible ; il se pilote lui-même dans une boucle ReAct
(observer → raisonner → agir) jusqu'à produire un rapport.

\`\`\`bash
python3 agent.py 192.168.56.50 --host http://<ip-serveur-ia>:11434                # recon + rapport
python3 agent.py 192.168.56.50 --host http://<ip-serveur-ia>:11434 --exploit      # recon, puis exploitation
\`\`\`

Déroulé : recon nmap → énumération par port → (optionnel) exploitation →
post-exploitation → rapport.

**Le LLM décide et analyse ; l'orchestrateur détient les faits.** Les services
ouverts, les résultats d'exploitation et la collecte post-exploitation du
rapport sont construits à partir des sorties réelles des outils, jamais récités
par le modèle. Le rapport ne peut donc pas halluciner un port ou un shell.

### Exploitation

L'exploitation est **désactivée par défaut** et ne s'active qu'avec \`--exploit\`.
Elle est volontairement bridée :

- **Allow-list uniquement.** L'agent n'exécute qu'un petit ensemble de modules
  Metasploit vérifiés, jamais un module arbitraire.
- **Scope revérifié.** Chaque exploitation revérifie que la cible est bien dans
  \`scope.txt\`.
- **Portable.** Le \`LHOST\` du reverse shell est auto-détecté depuis la route vers
  la cible : aucune IP en dur, ça marche sur n'importe quel réseau.
- **Adaptatif.** Si un module n'ouvre pas de session, l'agent bascule seul sur un
  autre module correspondant à un service ouvert avant d'abandonner.

Ajouter un module = une seule entrée dans \`exploit_tool.py\`.

### Post-exploitation

Une fois un shell root obtenu, l'agent démontre l'**impact** — ce qu'un
attaquant récupérerait — sans jamais rien casser :

- **Allow-list en lecture seule.** Identité, infos système, fichiers de comptes
  et configuration réseau. Aucune exécution de commande arbitraire.
- **Non destructif.** Jamais de persistance, de backdoor, de destruction ni
  d'exfiltration. On *prouve* l'impact, on ne cause aucun dégât réel.

### Architecture

Le projet sépare le cerveau des mains sur deux machines :

| Rôle     | Machine                 | Fonction |
|----------|-------------------------|----------|
| Cerveau  | Serveur IA (headless)   | Exécute le LLM. Reçoit un état, renvoie l'action suivante. Ne touche jamais la cible. |
| Mains    | Poste de pilotage (Kali)| Orchestrateur Python + outils de pentest. Vérifie le scope, lance les outils, renvoie les résultats au cerveau. |

L'adresse du serveur n'est jamais en dur : l'orchestrateur la lit depuis \`--host\`
(ou la variable d'environnement \`OLLAMA_HOST\`), donc aucun détail
d'infrastructure ne vit dans le dépôt.

### Stack technique

- Langage : Python 3
- LLM local : Ollama — modèle retenu : \`qwen2.5:7b\`
- Reconnaissance : nmap
- Exploitation : Metasploit Framework (msfconsole)
- Serveur IA : Ubuntu Server 24.04 LTS, NVIDIA RTX 4060 (8 Go VRAM)

### Installation

\`\`\`bash
pip install -r requirements.txt
cp scope.txt.example scope.txt     # puis éditer : une IP ou un CIDR par ligne
python3 agent.py <ip-cible> --host http://<ip-serveur-ia>:11434 --exploit
\`\`\`

\`scope.txt\` et les rapports générés restent locaux (git-ignorés) : ils décrivent
votre propre labo.

### Options principales

| Option            | Rôle |
|-------------------|------|
| \`target\`          | IP de la cible à évaluer (doit être dans le scope). |
| \`-H\`, \`--host\`    | URL du serveur Ollama (défaut : \`$OLLAMA_HOST\` ou localhost). |
| \`-s\`, \`--scope\`   | Fichier de scope (défaut : \`scope.txt\`). |
| \`-m\`, \`--model\`   | Nom du modèle (défaut : \`qwen2.5:7b\`). |
| \`--max-steps\`     | Nombre max d'étapes de raisonnement (défaut : 8). |
| \`--exploit\`       | Active l'exploitation (désactivée par défaut). |

---

## 🇬🇧 English

An autonomous penetration-testing agent driven by a local LLM. You give it a
single target; it runs the whole mission on its own: reconnaissance,
vulnerability identification, exploitation, non-destructive post-exploitation,
and a written report.

This is not a chatbot: it is an **agent** that decides and acts in a loop until
it produces the final report.

Study / portfolio project — designed to run **only** in an isolated lab.

### ⚠️ Legal & ethical scope (read this first)

This project **exploits** real vulnerabilities and can open a root shell on its
target. Run it **only** against:

- vulnerable virtual machines you own, on an isolated network, or
- systems for which you hold explicit written authorization.

Using it against any other system is illegal. In France, unauthorized access to
a computer system is punished under articles 323-1 et seq. of the Code pénal;
most countries have equivalent laws.

A **scope guardrail** sits at the core of the architecture: every tool refuses to
act on a target not listed in the declared rules-of-engagement file
(\`scope.txt\`). This check is hard-coded into each tool, recon and exploitation
alike.

### How it works

You launch the agent with a target; it drives itself in a ReAct loop
(observe → reason → act) until it produces a report.

\`\`\`bash
python3 agent.py 192.168.56.50 --host http://<ai-server-ip>:11434                # recon + report only
python3 agent.py 192.168.56.50 --host http://<ai-server-ip>:11434 --exploit      # recon, then exploitation
\`\`\`

Mission flow: nmap recon → per-port enumeration → (optional) exploitation →
post-exploitation → report.

**The LLM only decides and analyses; the orchestrator owns the facts.** The open
services, exploitation results, and post-exploitation collection in the report
are built from real tool output, never from the model, so the report cannot
hallucinate a port or a shell.

### Exploitation

Exploitation is **off by default** and only enabled with \`--exploit\`. It is
deliberately constrained:

- **Allow-list only.** The agent runs a small set of vetted Metasploit modules,
  never an arbitrary one.
- **Scope-checked.** Every exploit re-verifies the target is in \`scope.txt\`.
- **Portable.** The reverse-shell \`LHOST\` is auto-detected from the route to the
  target, so it works on any network without editing the code.
- **Adaptive.** If one module yields no session, the agent falls back to another
  module matching an open service before giving up.

Adding a module is a single entry in \`exploit_tool.py\`.

### Post-exploitation

Once a root shell is obtained, the agent demonstrates **impact** — what an
attacker would recover — without ever causing damage:

- **Read-only allow-list.** Identity, system info, account files, and network
  configuration. No arbitrary command execution.
- **Non-destructive.** No persistence, backdoor, destruction, or exfiltration. It
  *proves* impact; it causes no real harm.

### Architecture

The project separates the brain from the hands across two machines:

| Role  | Machine              | Function |
|-------|----------------------|----------|
| Brain | AI server (headless) | Runs the LLM. Takes a state, returns the next action. Never touches the target. |
| Hands | Control host (Kali)  | Python orchestrator + pentest tools. Checks scope, runs the tools, feeds results back to the brain. |

The server address is never hard-coded: the orchestrator reads it from \`--host\`
(or the \`OLLAMA_HOST\` environment variable), so no infrastructure detail lives in
the repository.

### Tech stack

- Language: Python 3
- Local LLM: Ollama — model tested: \`qwen2.5:7b\`
- Recon: nmap
- Exploitation: Metasploit Framework (msfconsole)
- AI server: Ubuntu Server 24.04 LTS, NVIDIA RTX 4060 (8 GB VRAM)

### Setup

\`\`\`bash
pip install -r requirements.txt
cp scope.txt.example scope.txt     # then edit: one IP or CIDR per line
python3 agent.py <target-ip> --host http://<ai-server-ip>:11434 --exploit
\`\`\`

\`scope.txt\` and generated reports stay local (git-ignored): they describe your
own lab.

### Main options

| Option            | Purpose |
|-------------------|---------|
| \`target\`          | Target IP to assess (must be in scope). |
| \`-H\`, \`--host\`    | Ollama server URL (default: \`$OLLAMA_HOST\` or localhost). |
| \`-s\`, \`--scope\`   | Scope file (default: \`scope.txt\`). |
| \`-m\`, \`--model\`   | Model name (default: \`qwen2.5:7b\`). |
| \`--max-steps\`     | Max reasoning steps (default: 8). |
| \`--exploit\`       | Enable exploitation (off by default). |

---

## Repository layout · Structure du dépôt

| File | Purpose · Rôle |
|------|----------------|
| \`agent.py\`           | Orchestrator + ReAct loop: drives the mission and writes the report. |
| \`nmap_tool.py\`       | Reconnaissance: scope-checked \`nmap -sV\` service scan. |
| \`enum_tool.py\`       | Per-port enumeration: scope-checked nmap vulnerability scripts. |
| \`exploit_tool.py\`    | Exploitation: scope-checked, allow-listed Metasploit modules. |
| \`postexploit_tool.py\`| Non-destructive post-exploitation: read-only impact collection. |
| \`scope.py\`           | The central safeguard: decides whether a target is in scope. |
| \`scope.txt.example\`  | Template rules-of-engagement file (copy to \`scope.txt\`). |
| \`requirements.txt\`   | Python dependencies. |
| \`BENCHMARK.md\`       | Model comparison (why \`qwen2.5:7b\` was chosen). |

## Requirements · Prérequis

- Python 3 with \`requests\` (\`pip install -r requirements.txt\`)
- \`nmap\` and \`metasploit-framework\` on the control host (preinstalled on Kali)
- A reachable Ollama server with the model pulled (\`ollama pull qwen2.5:7b\`)

## Roadmap

- [x] AI server up and running (Ubuntu + GPU driver + Ollama)
- [x] Model downloaded and tested (\`qwen2.5:7b\`)
- [x] Expose the LLM API on the private network
- [x] Harden the server (SSH key, firewall, fail2ban)
- [x] Orchestrator ↔ LLM API dialogue
- [x] Scope guardrail: refuse any out-of-scope target
- [x] Recon tool: nmap against an in-scope target
- [x] Full agentic loop with scope enforcement
- [x] Findings report generation
- [x] Vulnerable-VM lab for testing
- [x] Exploitation: allow-listed modules, scope-checked, adaptive fallback
- [x] Non-destructive post-exploitation: read-only impact collection
- [ ] Tool registry to make adding tools trivial
- [ ] Human-in-the-loop escalation after repeated failures
- [ ] More exploit modules and lab targets (DVWA, VulnHub, HTB)
- [ ] Persistent Metasploit instance (\`msfrpcd\`) to cut startup latency

## Inspirations

Open-source projects studied for inspiration: PentestGPT, Nebula, and agent
frameworks (AutoGPT / CrewAI) adapted for pentesting.

## License

Personal study project.
