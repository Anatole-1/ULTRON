# ULTRON — Manual (English)

> 🇫🇷 [MANUAL.fr.md](MANUAL.fr.md)

Give ULTRON one target IP; it runs recon → credentials → exploitation →
read-only post-exploitation → report, and can hand you an interactive shell.

**Lab only.** It runs real exploits. Only test machines you own or are authorized
to test — unauthorized use is illegal. Every tool refuses any IP not in
`scope.txt`, and the target always comes from the command line.

## Requirements

`nmap`, `metasploit` (`msfconsole`), `hydra`, `john`, `netexec` (`nxc`), Python 3 +
`requests` — all standard on Kali. The LLM modes also need a reachable **Ollama**
server; `--fast` needs nothing extra.

```bash
for t in python3 nmap msfconsole hydra john nxc; do command -v $t >/dev/null && echo "$t OK" || echo "$t MISSING"; done
```

## Setup

Put your in-scope target(s) in `scope.txt`, one IP per line:

```bash
cd ~/ia-pentest-autonome && printf '192.168.56.101\n' > scope.txt
```

## The three modes

| Mode | Flag | LLM? | When to use |
|---|---|---|---|
| Deterministic | `--fast` | no | Default. Fast and reliable on known services. |
| Hybrid | `--hybrid` | yes | Playbook drives; the LLM is asked only when it runs out of known moves. |
| LLM-first | *(neither)* | yes | The LLM picks every step. Slower, weaker with a small model. |

## Quick start

Replace `192.168.56.101` with your target.

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast -y
```
Recon only (no exploitation).

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit -y
```
Full deterministic attack.

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --shell
```
Same, and drops you an interactive root/SYSTEM shell when it lands.

## Options

| Option | Default | Meaning |
|---|---|---|
| `target` | — | Target IP (must be in scope). Required. |
| `--exploit` | off | Enable exploitation. Recon/creds still run without it. |
| `--shell` | off | Interactive root/SYSTEM shell after a successful exploit. |
| `--fast` | off | Deterministic playbook, no LLM. |
| `--hybrid` | off | Playbook + LLM fallback on the unknown (needs Ollama). |
| `--guided` | off | Confirm or redirect each action (and each LLM suggestion). |
| `--wordlist` | `builtin` | `builtin` / `common` / `rockyou`. |
| `-y` | off | Auto-approve; never pause (unattended runs). |
| `-H`, `--host` | localhost | Ollama URL, e.g. `http://192.168.56.10:11434`. |
| `-m`, `--model` | `qwen3:8b` | LLM model name. |
| `-s`, `--scope` | `scope.txt` | Scope file. |
| `--think` | off | Let the model reason internally (slower). |
| `--max-steps` | 8 | Max reasoning steps. |

## What the agent does

`nmap` → `smb_enum` (if SMB open) → **MS17-010 exploit** if vulnerable → SMB
credential **spray** → matching **exploit** module → **hydra** on auth services →
credential **reuse** → (hybrid) **LLM fallback** on anything unhandled → report.
It stops exploiting as soon as it gets a shell. `--exploit` gates every attacking
step; without it, only recon/enumeration/credentials run.

## The interactive shell (`--shell`)

- **Windows:** you land at `meterpreter >`. Type `getuid` (`NT AUTHORITY\SYSTEM`)
  or `shell` for `cmd.exe`. Enter works normally.
- **Linux:** a Meterpreter session, or a **raw root shell** if the upgrade fails.
  On a raw shell, if Enter prints `^M` instead of submitting, **use `Ctrl+J`**.
- **Leave:** `exit`, then `exit -y` at the `msf >` prompt. Your terminal is
  restored automatically.

## Reports & logs

Each run writes a Markdown report to `reports/<ip>_<time>.md` and a full terminal
transcript to `logs/<ip>_<time>.log`. Both are git-ignored.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `0 open services` in ~2 s | Target is off/unreachable — power it on, check the network. |
| `ping` fails but scan works | Normal; VMs often drop ICMP. ULTRON uses `-Pn`. |
| `no session` after an exploit | Target off, or a finicky/overused service. Re-run; let the VM recover. |
| `cannot reach the Ollama server` | Only affects `--hybrid`/LLM. Check `--host`, or use `--fast`. |
| Enter prints `^M` in a shell | Raw Linux shell — submit with `Ctrl+J`. Terminal stuck after exit? `stty sane` + `Ctrl+J`. |
| `REFUSED ... not in scope` | Add the IP to `scope.txt`. |
