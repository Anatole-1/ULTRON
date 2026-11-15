# Tested targets — ULTRON validation lab

The vulnerable virtual machines ULTRON has been validated against, and how each
one is reached by the agent. Everything here runs in an **isolated lab** (no
Internet exposure). Only publicly-known, deliberately-vulnerable practice VMs are
listed; their well-known default credentials are public and not secret.

> **No real addresses here.** Target IPs are DHCP and live only in your local
> `scope.txt` (git-ignored). Put each VM's current IP there before running ULTRON.

## Network setup (generic)

- Targets are VirtualBox VMs in **bridged** mode on a wired adapter, so a separate
  attacker host (Kali) on the LAN can reach them over TCP.
- Several of these VMs **drop ICMP** (ping fails) but are fully reachable over TCP
  — this is why every ULTRON tool uses `nmap -Pn`.
- DHCP addresses can change on reboot; re-check and update `scope.txt`.

---

## Linux targets

### Metasploitable 2
- **Source:** Rapid7 Metasploitable 2 (classic vulnerable Linux).
- **Key exposure:** vsftpd 2.3.4 backdoor; Samba 3.x `usermap_script`; many open
  auth services (ftp, ssh, telnet, mysql, postgres…).
- **How ULTRON handles it:** `exploit` via `vsftpd_234_backdoor` or
  `samba_usermap_script` → root shell; `hydra` on ftp finds weak logins
  (e.g. `msfadmin:msfadmin`, `user:user`, `postgres:postgres`); `reuse` replays
  them on the other services.
- **Validated result:** root shell + read-only post-exploitation.
- **Note:** vsftpd's backdoor port is near single-use; let the VM recover between
  back-to-back exploit runs.

### VulnHub — Basic Pentesting 1
- **Source:** VulnHub "Basic Pentesting 1".
- **Key exposure:** ProFTPD 1.3.3c compromised-source backdoor.
- **How ULTRON handles it:** `exploit` via `proftpd_133c_backdoor`.
- **Validated result:** root shell confirmed.

### VulnHub — Kioptrix Level 1
- **Source:** VulnHub "Kioptrix Level 1" (very old RedHat 7.2, ~2001).
- **Key exposure:** Samba 2.2.x `trans2open` stack overflow. This ancient Samba
  advertises no version, so the module trigger is the generic "Samba smbd".
- **How ULTRON handles it:** `exploit` via `samba_trans2open` (native
  `linux/x86/shell_reverse_tcp` payload).
- **Validated result:** root shell confirmed.
- **Notes:** drops ICMP; has no `ip` command (ULTRON's network collection falls
  back to `ifconfig`). The raw shell has no pty — ULTRON stabilizes it and reminds
  you to submit lines with `Ctrl+J`.

---

## Windows targets

### Windows Server 2008 R2 (Metasploitable3-style, deliberately vulnerable)
- **Source:** a Metasploitable3-style Windows Server 2008 R2 lab VM.
- **Intended weaknesses:** SMBv1 enabled, SMB signing off, **MS17-010 vulnerable
  (EternalBlue family)**, a weak local administrator account
  (`Administrator:vagrant`, plus `vagrant:vagrant`), and at least one readable
  share.
- **How ULTRON handles it (two independent paths):**
  1. **Credential-less:** `smb_enum` flags MS17-010 vulnerable → `win_exploit`
     (`ms17_010_psexec`) → **SYSTEM** shell, no credentials needed.
  2. **Credential-based:** `nxc_spray` finds `Administrator:vagrant` (local admin)
     → lists shares → read-only Windows collection; `--shell` opens a SYSTEM shell
     via psexec.
- **Validated result:** SYSTEM / local-admin compromise by either path. When one
  path missed (target hammered), the agent fell back to the other and still won.
- **Firewall note:** for a wormable vuln like MS17-010 on a real LAN, restrict the
  SMB port (445) to the attacker host only, to avoid exposing the box to the rest
  of the network.

### Windows 11 (hardened host — negative / honesty test)
- **Role:** a patched, hardened Windows host (not meant to be exploited).
- **What it shows:** only 135/tcp (RPC) and 445/tcp (SMB) open, **SMB 3.1.1 with
  message signing required**, no null/guest access, no weak creds.
- **How ULTRON handles it:** `smb_enum` honestly reports the hardened posture;
  `nxc_spray` finds no credentials and says so; the hybrid LLM fallback is
  exercised here (playbook runs out of known moves → the model suggests one more
  allow-listed action).
- **Validated result:** **no compromise — by design.** Used to confirm ULTRON
  reports an in-scope but hardened host honestly instead of inventing findings.

---

## Coverage summary

| Target | Type | Entry point | ULTRON module / step | Result |
|---|---|---|---|---|
| Metasploitable 2 | Linux | vsftpd 2.3.4 / Samba 3 / weak creds | `vsftpd_234_backdoor`, `samba_usermap_script`, `hydra`, `reuse` | root |
| Basic Pentesting 1 | Linux | ProFTPD 1.3.3c | `proftpd_133c_backdoor` | root |
| Kioptrix Level 1 | Linux | Samba 2.2.x | `samba_trans2open` | root |
| WS 2008 R2 (vuln) | Windows | MS17-010 / weak admin | `ms17_010_psexec` **or** `nxc_spray`+psexec | SYSTEM / admin |
| Windows 11 (hardened) | Windows | — | `smb_enum`, `nxc_spray`, LLM fallback | no compromise (expected) |

*All testing was performed in an isolated, authorized lab.*
