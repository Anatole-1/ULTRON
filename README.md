# ULTRON · scope-gated pentest orchestrator (optional local-LLM brain)
# Orchestrateur de pentest borné au scope · cerveau LLM local optionnel

ULTRON takes **one target IP** and runs the whole chain itself — recon →
credential attacks → exploitation → non-destructive post-exploitation → report —
and can hand you an interactive **root/SYSTEM shell**. A deterministic,
scope-gated orchestrator drives it; a local LLM is optional and only steps in on
the *unknown*. With a small model like `qwen3:8b` the deterministic playbook
(`--fast`) is the reliable path.

ULTRON prend **une IP cible** et déroule toute la chaîne seul — reconnaissance →
credentials → exploitation → post-exploitation non destructive → rapport — et peut
vous rendre un **shell root/SYSTEM** interactif. Un orchestrateur déterministe
borné au scope pilote ; le LLM local est optionnel et n'intervient que sur
l'*inconnu*. Avec un petit modèle comme `qwen3:8b`, le playbook déterministe
(`--fast`) est le chemin fiable.

> ⚠️ **Lab only / Labo uniquement.** Runs real exploits and can open a root shell.
> Use it only on VMs you own or have written authorization for — unauthorized use
> is illegal. A hard-coded scope guardrail makes every tool refuse any target
> absent from `scope.txt`. The target always comes from the command line (the LLM
> can't change it). Full guide: **[MANUAL.md](MANUAL.md)** · **[MANUAL.fr.md](MANUAL.fr.md)**.

## What it does · Ce qu'il fait

- **Scope guardrail** — every tool refuses a target that isn't in `scope.txt`.
- **Recon** — `nmap` + Windows-aware SMB enumeration (OS, signing, shares, `ms17-010`).
- **Credentials** — hydra on open auth services, credential **reuse** across them,
  and offline `/etc/shadow` cracking (john) on Linux; SMB **spraying** (`nxc`) on Windows.
- **Exploitation** (`--exploit`, off by default) — allow-listed Metasploit modules
  (vsftpd 2.3.4, Samba usermap, ProFTPD 1.3.3c, Samba trans2open) plus
  **credential-less MS17-010** (SYSTEM, no kernel shellcode).
- **Post-exploitation** — read-only collection only (identity, accounts, hashes,
  network). No persistence, destruction or exfiltration.
- **Interactive shell** (`--shell`) — a real root/SYSTEM shell with a robust
  handoff: it finds the session at runtime, falls back to a raw shell if a
  Meterpreter upgrade dies, stabilizes the TTY, and restores your terminal after.
- **Three modes** — `--fast` (deterministic, no LLM), `--hybrid` (playbook + LLM
  only when it runs out of known moves), or LLM-first (default). `--guided` lets
  you accept/redirect every action.
- Each run writes a timestamped transcript to `logs/`.

## Usage

```bash
pip install -r requirements.txt
cp scope.txt.example scope.txt          # one IP or CIDR per line

python3 agent.py <target-ip> --fast --exploit                 # deterministic, no LLM
python3 agent.py <target-ip> --fast --exploit --shell         # + interactive root/SYSTEM shell
python3 agent.py <target-ip> --hybrid --exploit --host http://<ai-server>:11434   # + LLM on the unknown
python3 agent.py <target-ip> --host http://<ai-server>:11434 --exploit            # LLM-first (default)
```

| Flag | Purpose · Rôle |
|------|----------------|
| `--exploit` | Enable exploitation (off by default) · active l'exploitation. |
| `--shell` | Interactive root/SYSTEM shell after a successful exploit · shell interactif. |
| `--fast` | Deterministic playbook, no LLM / no AI server · playbook déterministe. |
| `--hybrid` | Playbook + LLM fallback on the unknown (needs Ollama) · + secours LLM. |
| `--guided` | Validate or redirect each action · valider/rediriger chaque action. |
| `--wordlist` | `builtin` / `common` / `rockyou` credential list · niveau de wordlist. |
| `-y` · `--think` · `-m` · `-H` · `-s` | auto-approve · model reasoning · model · Ollama host · scope file. |

## Requirements · Prérequis

Python 3 + `requests`, and `nmap` / `hydra` / `john` / `metasploit-framework` /
`netexec` (preinstalled on Kali). The `--hybrid` and LLM-first modes also need a
reachable Ollama server (`ollama pull qwen3:8b`); `--fast` needs none.

---

*Personal study project. Lab use only.*
