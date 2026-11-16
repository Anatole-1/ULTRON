# ULTRON · scope-gated pentest orchestrator (optional local-LLM brain)
# Orchestrateur de pentest borné au scope · cerveau LLM local optionnel

ULTRON runs a full pentest chain on a target — recon → credential attacks →
vulnerability ID → exploitation → non-destructive post-exploitation → written
report — and can hand you an interactive Meterpreter root shell. The chain is
driven by a **deterministic, scope-gated orchestrator**; an optional local-LLM
layer (ReAct loop) can pick each action instead, but it is only as good as the
local model — with a small model like `qwen3:8b` it stays limited, so the
deterministic playbook (`--fast`) is the reliable path. Study / portfolio project.

ULTRON déroule toute une chaîne de pentest sur une cible — reconnaissance →
attaque de credentials → identification de vulnérabilités → exploitation →
post-exploitation non destructive → rapport — et peut vous rendre un shell root
Meterpreter interactif. La chaîne est pilotée par un **orchestrateur déterministe
et borné au scope** ; une couche LLM locale optionnelle (boucle ReAct) peut
choisir chaque action à la place, mais elle ne vaut que le modèle local — avec un
petit modèle comme `qwen3:8b` elle reste limitée, donc le playbook déterministe
(`--fast`) est le chemin fiable. Projet d'étude / portfolio.

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

Deux modes d'exécution. Le mode par défaut est une **boucle ReAct pilotée par le
LLM** (observer → raisonner → agir) : recon nmap → énumération par port → attaque
de credentials → (optionnel) exploitation → post-exploitation → rapport. Le mode
`--fast` est une **playbook déterministe** en code pur qui déroule la même chaîne
**sans LLM ni serveur IA**. La boucle LLM ne vaut que le modèle local : avec un
petit modèle comme `qwen3:8b` elle est limitée (JSON bancal, actions invalides
re-promptées, CVE hallucinées filtrées), donc en pratique le playbook
déterministe est le chemin le plus fiable.

**Quand le LLM est activé, il décide et analyse ; l'orchestrateur détient les
faits et la sécurité.** Services ouverts, résultats d'exploitation, credentials et
collecte post-exploitation sont construits à partir des sorties réelles des
outils, jamais récités par le modèle. La cible vient toujours de la ligne de
commande (le modèle ne peut pas la changer).

- **Registre d'outils extensible** : ajouter un outil = une entrée + une fonction.
  Chaque outil peut porter un *hint* qui dit au modèle quand l'utiliser.
- **Attaque de credentials** (`hydra`) : brute-force des services d'auth ouverts
  (ftp, telnet…) avec une petite liste de mots de passe faibles ; les identifiants
  trouvés sont affichés en direct et listés dans le rapport.
- **Niveaux de wordlist** (`--wordlist builtin|common|rockyou`) : `builtin`
  (défaut labo, court et rapide), `common` (liste de John) ou `rockyou` (fuite
  classique). Borné : hydra ne teste que le top-2000 (rockyou est trié par
  fréquence) et rockyou est décompressé **une fois** en cache ; john reçoit la
  liste complète (limité par le temps, pas le nombre). Le niveau s'applique aux
  deux chemins (LLM et `--fast`).
- **Exploitation** (off par défaut, `--exploit`) : allow-list de modules Metasploit
  vérifiés (vsftpd 2.3.4, Samba usermap 3.x, ProFTPD 1.3.3c, Samba trans2open 2.2.x),
  scope revérifié, `LHOST` auto, déclencheur par module.
- **Cibles Windows (SMB)** : énumération SMB Windows-aware (NSE : OS, signature,
  partages, `ms17-010`) ; **spray de credentials** (`nxc`/netexec, defaults faibles,
  `--local-auth`) avec repérage des comptes admin et des partages ; **exécution
  authentifiée** (collecte read-only + shell **SYSTEM** via psexec) ; et **MS17-010**
  comme voie d'accès **sans credentials** (famille EternalBlue, SYSTEM, via named
  pipe — pas de shellcode kernel).
- **Post-exploitation** : une fois root, collecte **en lecture seule** (identité,
  comptes, hashes, réseau). Jamais de persistance, destruction ou exfiltration.
- **Capture de session** : en plus du rapport, chaque run écrit un transcript
  horodaté dans `logs/` — tout ce qui défile dans le terminal, écrit en continu
  (survit à un crash). Le handoff `--shell` interactif n'y est pas capturé.
- **Shell interactif** (`--shell`, ou à la demande en mode guidé) : après un
  exploit réussi, l'agent vous rend la main sur un **shell root**. Il tente une
  session **Meterpreter** (plus confortable), mais la session cible est découverte
  dynamiquement et, si l'upgrade Meterpreter meurt (cibles fragiles, ex. Kioptrix),
  il **retombe automatiquement sur le shell brut root** au lieu de vous laisser en
  rade. Sur un shell brut, il **stabilise le TTY** (pose un vrai pty via
  python/`script`) pour que la touche Entrée fonctionne ; faute d'outil pty sur une
  cible très ancienne, validez les lignes avec `Ctrl+J`.
- **Mode guidé** (`--guided`) : avant chaque action, l'agent montre ce qu'il veut
  faire et **vous décidez** — accepter, remplacer par votre action, ou arrêter.
- **Mode rapide déterministe** (`--fast`) : une playbook en code pur pilote tout
  l'enchaînement (recon → exploit si un module matche → credentials → **réutilisation
  de credentials** sur les autres services via `hydra -C` → rapport), **sans LLM ni
  serveur IA**. Les mots de passe connus incluent ceux **cassés localement** depuis
  les hashes `/etc/shadow` collectés (john), au-delà de la wordlist hydra.
- **Mode hybride** (`--hybrid`) : le playbook déterministe pilote et n'appelle le
  LLM **que lorsqu'il n'a plus de coup connu** (service inconnu) — pour UNE action
  de l'allow-list (enum/exploit/hydra), validée (port ouvert, pas déjà fait, scope),
  et confirmable via `--guided`. Vitesse du déterministe + couverture du LLM.
  `--fast` reste 100% déterministe.
- **Human-in-the-loop** : approbation avant exploit, indice si l'agent bloque.
  `-y` = autonome sans question. Non destructif et scope-gated de bout en bout.

## 🇬🇧 English

Two execution modes. The default is an **LLM-driven ReAct loop** (observe →
reason → act): nmap recon → per-port enumeration → credential attacks →
(optional) exploitation → post-exploitation → report. The `--fast` mode is a
**deterministic, pure-code playbook** that runs the same chain with **no LLM and
no AI server**. The LLM loop is only as good as the local model: with a small
model like `qwen3:8b` it is limited (shaky JSON, invalid actions re-prompted,
hallucinated CVEs filtered out), so in practice the deterministic playbook is the
dependable path.

**When the LLM is enabled, it decides and analyses; the orchestrator owns the
facts and the safety.** Open services, exploitation results, credentials and
post-exploitation collection are built from real tool output, never recited by
the model. The target always comes from the command line (the model cannot
change it).

- **Extensible tool registry**: adding a tool = one entry + one function. Each tool
  may carry a *hint* telling the model when to use it.
- **Credential attacks** (`hydra`): brute-force open auth services (ftp, telnet…)
  with a small list of common weak passwords; found logins are shown live and
  listed in the report.
- **Wordlist levels** (`--wordlist builtin|common|rockyou`): `builtin` (fast lab
  default), `common` (John's list), or `rockyou` (the classic leak). Bounded:
  hydra only tries the top-2000 (rockyou is frequency-ordered) and rockyou is
  decompressed **once** into a cache; john gets the full list (time-bounded, not
  count-bounded). The level applies to both paths (LLM and `--fast`).
- **Exploitation** (off by default, `--exploit`): allow-listed Metasploit modules
  (vsftpd 2.3.4, Samba usermap 3.x, ProFTPD 1.3.3c, Samba trans2open 2.2.x),
  re-checked scope, auto-detected `LHOST`, per-module trigger.
- **Windows (SMB) targets**: Windows-aware SMB enumeration (NSE: OS, signing,
  shares, `ms17-010`); **credential spraying** (`nxc`/netexec, weak defaults,
  `--local-auth`) flagging admin logins and reachable shares; **authenticated
  execution** (read-only collection + a **SYSTEM** shell via psexec); and
  **MS17-010** as a **credential-less** way in (EternalBlue family, SYSTEM, over a
  named pipe — no kernel shellcode).
- **Post-exploitation**: once root, **read-only** collection (identity, accounts,
  hashes, network). No persistence, destruction, or exfiltration.
- **Session transcript**: besides the report, every run writes a timestamped log
  to `logs/` — everything printed to the terminal, flushed as it goes (survives a
  crash). The interactive `--shell` handoff is not captured.
- **Interactive shell** (`--shell`, or on demand in guided mode): after a
  successful exploit, the agent hands you a **root shell**. It tries a
  **Meterpreter** session (nicer), but the target session id is discovered at
  runtime and, if the Meterpreter upgrade dies (fragile targets, e.g. Kioptrix),
  it **falls back automatically to the raw root shell** instead of stranding you.
  On a raw shell it **stabilizes the TTY** (spawns a real pty via python/`script`)
  so the Enter key works; if no pty tool exists on a very old target, submit lines
  with `Ctrl+J`.
- **Guided mode** (`--guided`): before each action the agent shows what it wants
  to do and **you decide** — accept, replace with your own action, or stop.
- **Deterministic fast mode** (`--fast`): a pure-code playbook drives the whole
  chain (recon → exploit when a module matches → credentials → **credential reuse**
  across the other services via `hydra -C` → report), with **no LLM and no AI
  server**. Known passwords include ones **cracked locally** from the collected
  `/etc/shadow` hashes (john), beyond hydra's wordlist.
- **Hybrid mode** (`--hybrid`): the deterministic playbook drives and calls the LLM
  **only when it runs out of known moves** (an unknown service) — for ONE
  allow-listed action (enum/exploit/hydra), validated (open port, not already done,
  in scope) and confirmable via `--guided`. Deterministic speed + LLM coverage;
  `--fast` stays 100% deterministic.
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
python3 agent.py <target-ip> --fast --exploit                                   # deterministic playbook only (no LLM / no AI server)
python3 agent.py <target-ip> --fast --exploit --shell                           # + an interactive root/SYSTEM shell
python3 agent.py <target-ip> --hybrid --exploit --host http://<ai-server-ip>:11434   # deterministic + LLM fallback on the unknown
```

Full step-by-step guide: **[MANUAL.md](MANUAL.md)** (English) · **[MANUAL.fr.md](MANUAL.fr.md)** (Français).
Vulnerable VMs used to validate ULTRON: **[TESTED_TARGETS.md](TESTED_TARGETS.md)**.

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
| `--fast`             | Deterministic playbook only, no LLM / no AI server · playbook déterministe, sans LLM. |
| `--hybrid`           | Playbook + LLM fallback only on the unknown (needs Ollama) · playbook + secours LLM sur l'inconnu. |
| `--wordlist`         | Credential list level: `builtin`/`common`/`rockyou` · niveau de wordlist. |
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
| `agent.py`            | Orchestrator + ReAct loop, deterministic playbook (`--fast`), tool registry, guided mode, report builder. |
| `nmap_tool.py`        | Recon: scope-checked `nmap -Pn -sV` scan (host discovery off, so ICMP-filtered targets aren't skipped). |
| `enum_tool.py`        | Per-port enumeration (nmap vuln scripts) + Windows-aware SMB enumeration (`run_smb_enum`). |
| `hydra_tool.py`       | Credential attack: scope-checked hydra, wordlist level from `wordlists.py`. |
| `nxc_tool.py`         | Windows SMB credential attacks (spray), authenticated execution and read-only collection via `nxc`/netexec. |
| `wordlists.py`        | Named wordlist levels (builtin/common/rockyou), shared by hydra and john; bounded + cached. |
| `exploit_tool.py`     | Exploitation: scope-checked, allow-listed Metasploit modules (Linux + Windows MS17-010). |
| `postexploit_tool.py` | Non-destructive post-exploitation + robust interactive shell handoff (Linux raw/Meterpreter, Windows SYSTEM). |
| `crack_tool.py`       | Local password cracking (john) on collected hashes, to feed credential reuse. |
| `scope.py`            | The central safeguard: is a target in scope? |
| `scope.txt.example`   | Template scope file (copy to `scope.txt`). |
| `requirements.txt`    | Python dependencies (`requests`). |
| `MANUAL.md` · `MANUAL.fr.md` | Full bilingual user manual (EN/FR). |
| `TESTED_TARGETS.md`   | The validation lab: vulnerable VMs used to test ULTRON. |
| `BENCHMARK.md`        | Model comparison (why `qwen3:8b`). |

## Requirements · Prérequis

- Python 3 + `requests` · nmap + hydra + john + metasploit-framework + netexec
  (`nxc`, for Windows/SMB) — all preinstalled on Kali
- (LLM / `--hybrid` modes only) a reachable Ollama server with the model pulled
  (`ollama pull qwen3:8b`); not needed for `--fast`

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
- [x] Deterministic playbook + fast mode (`--fast`), no LLM, with credential reuse
- [x] Local hash cracking (john) on collected `/etc/shadow`, feeding credential reuse
- [x] LLM fallback only on unknown service/version (hybrid playbook + model, `--hybrid`)
- [x] More exploit modules and lab targets: ProFTPD 1.3.3c + Samba trans2open
  modules, validated with root shells on VulnHub Basic Pentesting 1 & Kioptrix 1
- [x] Larger wordlists for credential attacks (`--wordlist common|rockyou`, bounded + cached)
- [x] Windows generalization: SMB enumeration, credential spraying (`nxc`),
  authenticated execution + SYSTEM shell, and credential-less MS17-010
- [x] Bilingual user manual + documented validation lab

## Inspirations · License

Studied for inspiration: PentestGPT, Nebula, and agent frameworks (AutoGPT /
CrewAI) adapted for pentesting. Personal study project.
