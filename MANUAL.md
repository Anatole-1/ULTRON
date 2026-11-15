# ULTRON — User Manual (English)

> 🇫🇷 Version française : [MANUAL.fr.md](MANUAL.fr.md)

ULTRON is an **autonomous penetration-testing agent**. You give it one target IP
and it runs the whole mission by itself: reconnaissance → credential attacks →
exploitation → read-only post-exploitation → report.

**Honest positioning.** ULTRON is first a **deterministic orchestrator** bounded
by a declared scope. A local LLM is an **optional brain** that only helps on the
*unknown*. The reliable work is done by the deterministic playbook; the LLM is a
bonus, not a requirement.

---

## ⚠️ 1. Authorization & scope — READ FIRST

ULTRON only ever acts on targets listed in a **scope file** (`scope.txt`). This
is enforced **in every tool** (nmap, enum, SMB, hydra, exploit, post-exploit,
shell) — an out-of-scope target is refused even in autonomous mode.

- Only test machines you **own** or have **explicit written authorization** to test.
- Use an **isolated lab**. Attacking a third party without consent is illegal
  (in France: art. 323 of the Penal Code).
- The target **always comes from the command line**; the agent ignores any IP the
  LLM might suggest (anti-hallucination).

---

## 2. Requirements

On the Kali/Linux machine that runs the agent:

- **Python 3** and the `requests` library.
- **nmap**, **Metasploit** (`msfconsole`), **hydra**, **john** (John the Ripper),
  **netexec** (`nxc`) — standard on Kali.
- (Optional, only for the LLM modes) an **Ollama** server reachable on the
  network, e.g. with the `qwen3:8b` model.

Check what you have:

```bash
for t in python3 nmap msfconsole hydra john nxc; do command -v $t >/dev/null && echo "$t OK" || echo "$t MISSING"; done
```

---

## 3. First-time setup

Create your scope file and put the target IP(s) in it (one per line):

```bash
cd ~/ia-pentest-autonome && printf '192.168.56.101\n' > scope.txt
```

`scope.txt` is git-ignored (local only). Add every IP you are allowed to test.

If you use a Python virtual environment:

```bash
cd ~/ia-pentest-autonome && python3 -m venv venv && source venv/bin/activate && pip install requests
```

---

## 4. Quick start

Replace `192.168.56.101` with your in-scope target in all examples below.

**Recon only, no attack, no LLM** (safest first run):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast -y
```

**Full deterministic attack** (enable exploitation):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit -y
```

**Full attack and drop me an interactive root/SYSTEM shell** when it lands:

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --shell
```

---

## 5. The three modes

| Mode | Flag | LLM needed? | What it does |
|---|---|---|---|
| **Deterministic** | `--fast` | No | The playbook only. Fast, reliable, repeatable. Recommended default. |
| **Hybrid** | `--hybrid` | Yes | The playbook drives, and the LLM is consulted **only when the playbook runs out of known moves** (the "unknown"). Best of both. |
| **LLM-first** | *(no `--fast`/`--hybrid`)* | Yes | The LLM drives every step. Historical mode; slower and less reliable with a small local model. |

> Rule of thumb: use **`--fast`** for demos and known targets, **`--hybrid`** when
> you want the agent to try to reason about services it has no built-in rule for.

---

## 6. Command-line options

```
python3 agent.py <target-ip> [options]
```

| Option | Default | Meaning |
|---|---|---|
| `target` | — | Target IP (must be in the scope file). Positional, required. |
| `-s`, `--scope` | `scope.txt` | Path to the scope file. |
| `-H`, `--host` | `$OLLAMA_HOST` or `http://localhost:11434` | Ollama server URL (LLM/hybrid modes). |
| `-m`, `--model` | `qwen3:8b` | LLM model name on the Ollama server. |
| `--max-steps` | `8` | Max reasoning steps (the `--fast`/`--hybrid` playbook raises its own floor so busy hosts still finish). |
| `--exploit` | off | **Enable exploitation.** Off by default — recon/enum/credentials still run without it. |
| `--shell` | off | After a successful exploit, hand you an **interactive root/SYSTEM shell** (interactive terminal only). |
| `--guided` | off | Validate or redirect **each action** before it runs (interactive only). In `--hybrid`, you confirm each LLM suggestion. |
| `--fast` | off | Deterministic playbook only — **no LLM, no Ollama needed**. |
| `--hybrid` | off | Deterministic playbook + LLM fallback on the unknown (needs Ollama). |
| `--wordlist` | `builtin` | Credential list level: `builtin` (small/fast lab list), `common` (John's list), `rockyou` (capped for hydra, full for john). |
| `-y`, `--yes` | off | Auto-approve everything; never pause (use for unattended runs). |
| `--think` | off | Let the model reason internally (slower, richer; LLM modes). |

---

## 7. What the agent does (the playbook)

In `--fast` / `--hybrid`, the deterministic logic chooses the next action from the
current state, in this order:

1. **nmap** — scan the target (`-Pn -sV`, so hosts that drop ICMP are still seen).
2. **smb_enum** — if SMB (139/445) is open, run the Windows NSE set
   (`smb-os-discovery`, SMB signing, shares, sessions, `smb-vuln-ms17-010`).
3. **win_exploit** — if MS17-010 is flagged vulnerable *and* `--exploit` is set,
   get a **SYSTEM shell without credentials** (MS17-010 via named pipe).
4. **nxc_spray** — if `--exploit` is set, spray default/weak SMB credentials;
   on a valid admin login, list shares and run a read-only Windows collection.
5. **exploit** — if an open service matches a vetted Metasploit module in the
   allow-list (vsftpd, Samba usermap, ProFTPD, Samba trans2open) and `--exploit`
   is set, run it and collect read-only evidence.
6. **hydra** — brute-force open auth services (ftp, ssh, telnet, mysql, postgres).
7. **reuse** — replay every credential found against the other auth services.
8. (hybrid only) **LLM fallback** — when none of the above applies, ask the LLM
   for one more allow-listed action (e.g. enumerate an unusual port).
9. **finish** — write the report.

The agent stops exploiting as soon as it has a shell (it does not hammer the box).

---

## 8. Recipes

**Bigger password list** (opt-in, capped for online brute-force):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --fast --exploit --wordlist rockyou
```

**Hybrid run against an Ollama server** (replace the server IP with yours):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 -y
```

**Hybrid + guided** — the agent proposes, you decide (ENTER = accept, type an
action to redirect, `q` = stop):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 --guided
```

**Use a stronger model** (if available on your Ollama server):

```bash
cd ~/ia-pentest-autonome && python3 agent.py 192.168.56.101 --hybrid --exploit --host http://192.168.56.10:11434 --model qwen3.5:9b -y
```

---

## 9. Using the interactive shell (`--shell`)

When an exploit lands and you passed `--shell`, the agent hands you a live session:

- **Windows (MS17-010 / psexec):** you land at `meterpreter >`. Type `getuid`
  (shows `NT AUTHORITY\SYSTEM`), or `shell` for a `cmd.exe`. Enter works normally.
- **Linux:** you get a Meterpreter session if the upgrade succeeds, otherwise a
  **raw root shell**. On a raw shell the agent spawns a pty automatically, but the
  Enter key may still send `^M` without submitting — **submit each line with
  `Ctrl+J`** (the agent reminds you on screen).

**To leave the shell and let the agent finish:** type `exit`, then `exit -y` at the
`msf >` prompt. Your terminal is restored automatically (`stty sane`).

---

## 10. Reports and logs

- **Report:** a Markdown file is written to `reports/<ip>_<timestamp>.md`
  (open services, SMB enumeration, credentials, exploitation, read-only
  post-exploitation, analysis).
- **Transcript:** every run also writes `logs/<ip>_<timestamp>.log` — everything
  that scrolled in the terminal, flushed line by line (it survives a crash). The
  interactive `--shell` session itself is not captured (it runs on the real tty).

Both `reports/` and `logs/` are git-ignored.

---

## 11. Extending ULTRON (add an exploit)

Coverage grows by adding modules to the allow-list. For a Metasploit module, add
one entry to `MODULES` in [exploit_tool.py](exploit_tool.py) with a `trigger`
(the nmap service string that should fire it):

```python
"my_module_key": {
    "module": "exploit/linux/....",
    "payload": "cmd/unix/reverse_perl",
    "desc": "human description",
    "trigger": "ServiceName x.y.z",
},
```

That is the single most effective lever to make ULTRON bite on new targets.

---

## 12. Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| `0 open services` in ~2 s | The target VM is **off / unreachable**. Check it is powered on and on the same network. |
| `ping` fails but the scan works | Normal — many VMs drop ICMP. ULTRON uses `-Pn` everywhere. |
| `no session` after an exploit | Target may be off, or a finicky service (e.g. vsftpd's backdoor is near single-use). Re-run; let the VM recover between attempts. |
| `cannot reach the Ollama server` | Only affects `--hybrid` / LLM mode. Check the `--host` URL and that Ollama is running. Use `--fast` to work without it. |
| Enter prints `^M` in a shell | Raw Linux shell with no pty — **use `Ctrl+J`** to submit. If your terminal stays broken after exiting, type `stty sane` then `Ctrl+J`. |
| `REFUSED ... not in scope` | The target is not in `scope.txt`. Add it (one IP per line). |

---

*ULTRON is a study project for authorized, isolated lab use only.*
