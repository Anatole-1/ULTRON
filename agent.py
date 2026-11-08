"""Autonomous pentest agent (ReAct loop).

The LLM chooses each action; this orchestrator runs it through the
scope-enforced tools and feeds the result back, until a final report.
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime

import requests

from nmap_tool import run_nmap
from enum_tool import run_enum
from hydra_tool import run_hydra
from exploit_tool import MODULES
from postexploit_tool import run_postexploit, parse_collection, POST_COMMANDS, interactive_exploit


# Registry of simple recon/collection tools. Each runs as
# run(target, *extra_params, scope_file) and returns text or None (refused).
# Adding a recon tool = one entry here + its function. The prompt and the main
# loop pick it up automatically; exploitation is handled separately below.
TOOLS = {
    "nmap": {
        "desc": "broad service/version scan of a target IP.",
        "extra_params": [],
        "run": run_nmap,
        "is_scan": True,
    },
    "enum": {
        "desc": "deeper scan of ONE port on the target (runs nmap vulnerability scripts).",
        "extra_params": ["port"],
        "run": run_enum,
    },
    "hydra": {
        "desc": "brute-force login on ONE service of the target with a small list of common weak credentials. ftp and telnet are usually quickest; ssh is often slow or rejects old key exchanges.",
        "hint": "If an authentication service (ftp, telnet, ssh) is open, run hydra on it to try weak credentials (prefer ftp or telnet) before concluding.",
        "extra_params": ["service"],
        "run": run_hydra,
    },
}

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

# Minimum distinct services the agent must enumerate before it may conclude,
# unless a shell was already obtained or every open port is already enumerated.
MIN_ENUM_BEFORE_FINISH = 3

# Consecutive unproductive steps after which the agent asks a human for help
# (when interactive) or stops cleanly with a note (when unattended).
STUCK_LIMIT = 3


def ask_approval(question):
    """Returns 'yes', 'no', or 'all' (yes to all for the rest of the run)."""
    try:
        answer = input(f"[?] {question} [y/N/a=yes-to-all] ").strip().lower()
    except EOFError:
        return "no"
    if answer in ("a", "all", "tout"):
        return "all"
    if answer in ("y", "yes", "o", "oui"):
        return "yes"
    return "no"


def scrub_unverified_cves(text, corpus):
    """Drop any CVE id the model wrote that never appeared in what the agent
    actually observed. The orchestrator stays the source of truth for facts."""
    corpus_up = corpus.upper()
    return _CVE_RE.sub(
        lambda m: m.group(0) if m.group(0).upper() in corpus_up else "[unverified CVE removed]",
        text,
    )


def scan_ports(nmap_output):
    ports = []
    for line in nmap_output.splitlines():
        m = re.match(r"^(\d+)/tcp\s+open", line.strip())
        if m:
            ports.append(m.group(1))
    return ports


def build_prompt(exploit_enabled):
    tool_lines = [f"- {name}: {meta['desc']}" for name, meta in TOOLS.items()]
    action_keywords = list(TOOLS) + (["exploit"] if exploit_enabled else []) + ["finish"]
    extra_params = []
    for meta in TOOLS.values():
        for p in meta["extra_params"]:
            if p not in extra_params:
                extra_params.append(p)

    actions = "|".join(f'"{k}"' for k in action_keywords)
    fields = f'"thought": "...", "action": {actions}, "target": "<ip>"'
    for p in extra_params:
        fields += f', "{p}": "<{p}>"'

    exploit_rule = ""
    if exploit_enabled:
        modules = ", ".join(f"{k} (for {v['trigger']} - {v['desc']})" for k, v in MODULES.items())
        tool_lines.append(f"- exploit: launch a known exploit module against the target. Allowed modules: {modules}.")
        fields += ', "module": "<module key>"'
        exploit_rule = ("- As soon as nmap shows a service matching an allowed module (see its 'for ...' tag), "
                        "use 'exploit' with that EXACT module key BEFORE any further enum.\n"
                        "- Never 'exploit' a service or CVE that has no allowed module key, and never invent a module key.\n"
                        "- If an exploit returns no session or an unstable session, immediately try another untried allowed module before concluding.\n"
                        "- Do not keep enumerating services that have no matching module.\n"
                        "- A successful exploit automatically collects read-only impact; once it succeeds, finish.\n")
    fields += ', "report": "<findings>"'

    tool_list = "\n".join(tool_lines)
    keywords = ", ".join(action_keywords)
    tool_hints = "".join(f"- {meta['hint']}\n" for meta in TOOLS.values() if meta.get("hint"))
    return (
        "You are an autonomous penetration-testing agent operating in an authorized lab.\n"
        "You choose one action at a time; an external executor runs it and returns the result.\n\n"
        f"Tools available:\n{tool_list}\n\n"
        "Reply with ONE JSON object and nothing else:\n"
        f"  {{{fields}}}\n\n"
        "Rules:\n"
        f"- The 'action' field must be EXACTLY one keyword ({keywords}). Never put a sentence there.\n"
        "- Start with nmap. Then use enum on the most interesting or outdated service.\n"
        "- Enumerate SEVERAL interesting services before finishing; do not conclude after a single enum.\n"
        f"{tool_hints}"
        f"{exploit_rule}"
        "- Base every statement strictly on the observations returned to you. Never invent a port, service, version, or result.\n"
        "- Do not cite a CVE number unless it appears verbatim in an observation.\n"
        "- Do not repeat an action you have already performed.\n"
        "- Stay factual and terse: no greetings, no first person, no speculation.\n"
        "- For \"finish\", the \"report\" field contains exactly these two lines:\n"
        "  Notable findings: <outdated/risky services and any vulnerabilities or exploits confirmed>\n"
        "  Next steps: <concrete follow-up actions>"
    )


def as_text(value):
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


def truncate(text, limit=5000):
    return text if len(text) <= limit else text[:limit] + "\n... [output truncated]"


def parse_services(nmap_output):
    services = []
    for line in nmap_output.splitlines():
        if re.match(r"^\d+/tcp\s+open", line.strip()):
            services.append(" ".join(line.split()))
    return services


def exploit_result(output):
    low = output.lower()
    if "session" in low and "opened" in low:
        for line in output.splitlines():
            if line.strip().startswith("uid="):
                return f"shell opened ({line.strip()})"
        return "shell opened"
    return "no session"


def build_postexploit_section(collected):
    if not collected:
        return "_(no post-exploitation performed)_"
    blocks = []
    for label, cmd in POST_COMMANDS.items():
        body = collected.get(label)
        if body:
            blocks.append(f"### {label} — `{cmd}`\n```\n{body}\n```")
    return "\n\n".join(blocks) if blocks else "_(no data collected)_"


def build_report(target, services, exploits, postexploit, findings):
    service_lines = "\n".join(f"- {s}" for s in services) if services else "- (no nmap scan completed)"
    exploit_lines = "\n".join(f"- {e}" for e in exploits) if exploits else "- (none attempted)"
    return (
        f"# Pentest report - {target}\n\n"
        f"_Generated {datetime.now():%Y-%m-%d %H:%M}_\n\n"
        f"## Open services\n{service_lines}\n\n"
        f"## Exploitation\n{exploit_lines}\n\n"
        f"## Post-exploitation\n{build_postexploit_section(postexploit)}\n\n"
        f"## Analysis\n{findings if findings else '(model returned an empty report)'}\n"
    )


def ask_llm(host, model, messages, think=True):
    payload = {"model": model, "messages": messages, "stream": False, "format": "json"}
    if not think:
        payload["think"] = False
    error = "unknown error"
    for _ in range(2):
        try:
            resp = requests.post(f"{host}/api/chat", json=payload, timeout=120)
            resp.raise_for_status()
            data = json.loads(resp.json()["message"]["content"])
            return data if isinstance(data, dict) else {"action": "error", "thought": "model returned non-object JSON"}
        except requests.exceptions.RequestException as e:
            error = f"cannot reach the model server: {e}"
            payload.pop("think", None)  # some models reject 'think'; drop it and retry
        except (json.JSONDecodeError, KeyError):
            return {"action": "error", "thought": "model returned invalid JSON"}
    return {"action": "error", "thought": error}


def preflight(host, scope_file):
    problems = []
    if shutil.which("nmap") is None:
        problems.append("nmap is not installed or not on PATH.")
    if not os.path.exists(scope_file):
        problems.append(f"scope file not found: {scope_file} (copy scope.txt.example to scope.txt).")
    try:
        requests.get(f"{host}/api/tags", timeout=5).raise_for_status()
    except requests.exceptions.RequestException:
        problems.append(f"cannot reach the Ollama server at {host} (is it running?).")
    return problems


def run_tool(kind, action, scope_file, done, messages):
    """Generic handler for a registry tool. Returns its text output on success
    (so the caller can remember a scan), or None otherwise."""
    meta = TOOLS[kind]
    scan_target = as_text(action.get("target"))
    extra_values = []
    for param in meta["extra_params"]:
        value = as_text(action.get(param))
        if not value:
            messages.append({"role": "user", "content": f"Observation: {kind} requires a {param}."})
            return None
        extra_values.append(value)

    loc = scan_target + ("".join(f":{v}" for v in extra_values))
    key = (kind, scan_target, *extra_values)
    if key in done:
        print(f"    > skip (already ran {kind} on {loc})")
        messages.append({"role": "user", "content":
            f"Already ran {kind} on {loc}. Do not repeat it; use the result or finish."})
        return None

    print(f"    > {kind} {loc}")
    output = meta["run"](scan_target, *extra_values, scope_file)
    if output is None:
        messages.append({"role": "user", "content":
            f"Observation:\nREFUSED or invalid: {loc} is not in scope."})
        return None

    done.add(key)
    messages.append({"role": "user", "content": f"Observation:\n{truncate(output)}"})
    return output


def run_mission(host, model, scope_file, target, max_steps, exploit_enabled, interactive, think, shell_enabled):
    print(f"[*] target {target} | brain {model} @ {host}"
          + (" | exploit ON" if exploit_enabled else "")
          + ("" if interactive else " | non-interactive")
          + (" | thinking" if think else ""))
    messages = [
        {"role": "system", "content": build_prompt(exploit_enabled)},
        {"role": "user", "content": f"Assess target {target}. Decide the first action."},
    ]
    done = set()
    last_scan = None
    exploits = []
    postexploit = {}
    seen = []
    stuck = 0
    auto_approve = False

    for step in range(1, max_steps + 1):
        if stuck >= STUCK_LIMIT:
            if interactive:
                print(f"[!] Agent stuck after {stuck} unproductive steps.")
                hint = input("[?] Hint to unblock it (or ENTER to let it finish): ").strip()
                if hint:
                    messages.append({"role": "user", "content": f"Human hint: {hint}"})
                else:
                    messages.append({"role": "user", "content": "Human: no hint. Conclude with a finish now."})
                stuck = 0
            else:
                services = parse_services(last_scan) if last_scan else []
                note = "Agent stopped: stuck after repeated unproductive steps; human input needed."
                report = build_report(target, services, exploits, postexploit, note)
                print("\n" + report)
                print(f"[*] report saved to {save_report(target, report)}", file=sys.stderr)
                return

        action = ask_llm(host, model, messages, think)
        messages.append({"role": "assistant", "content": json.dumps(action)})
        print(f"\n[{step}] {as_text(action.get('thought'))}")

        kind = action.get("action")
        if kind in TOOLS:
            output = run_tool(kind, action, scope_file, done, messages)
            if output is not None:
                stuck = 0
                seen.append(output)
                if TOOLS[kind].get("is_scan"):
                    last_scan = output
            else:
                stuck += 1
        elif kind == "exploit":
            scan_target = as_text(action.get("target"))
            module_key = as_text(action.get("module"))
            if not exploit_enabled:
                messages.append({"role": "user", "content": "Observation: exploitation is disabled (run with --exploit)."})
                stuck += 1
                continue
            if ("exploit", scan_target, module_key) in done:
                print(f"    > skip (already tried {module_key} on {scan_target})")
                messages.append({"role": "user", "content":
                    f"Already tried {module_key} on {scan_target}. Use the result or finish."})
                stuck += 1
                continue
            if interactive and not auto_approve and module_key in MODULES:
                decision = ask_approval(f"Run exploit {module_key} on {scan_target}?")
                if decision == "all":
                    auto_approve = True
                elif decision == "no":
                    messages.append({"role": "user", "content":
                        f"Human declined exploit {module_key} on {scan_target}. Choose another action or finish."})
                    continue
            print(f"    > exploit {module_key} on {scan_target}")
            output = run_postexploit(scan_target, module_key, scope_file)
            if output is None:
                if module_key not in MODULES:
                    tried = {e[2] for e in done if e[0] == "exploit"}
                    choices = [k for k in MODULES if k not in tried] or list(MODULES)
                    observation = (f"Unknown module '{module_key}'. Use an EXACT allowed module key: "
                                   f"{', '.join(choices)}. Pick one matching an open service, or finish.")
                else:
                    observation = f"REFUSED: {scan_target} is not in scope."
                stuck += 1
            else:
                done.add(("exploit", scan_target, module_key))
                seen.append(output)
                outcome = exploit_result(output)
                exploits.append(f"{module_key} on {scan_target} -> {outcome}")
                if outcome == "no session":
                    observation = f"{module_key}: no shell obtained."
                    tried = {e[2] for e in done if e[0] == "exploit"}
                    remaining = [k for k in MODULES if k not in tried]
                    if remaining:
                        observation += (f" Untried exploit modules: {', '.join(remaining)}. "
                                        "Try one that matches an open service before finishing.")
                    stuck += 1
                else:
                    collected = parse_collection(output)
                    postexploit.update(collected)
                    if shell_enabled and interactive:
                        print("    > opening interactive shell on the target (msfconsole); type 'exit' to return...")
                        interactive_exploit(scan_target, module_key, scope_file)
                    labels = ", ".join(k for k in POST_COMMANDS if collected.get(k))
                    observation = (f"{module_key}: {outcome}. Read-only post-exploitation collected "
                                   f"({labels}) and recorded for the report. Impact is documented; you may finish.")
                    stuck = 0
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        elif kind == "finish":
            enum_ports = {e[2] for e in done if e[0] == "enum"}
            shell = any("shell opened" in e for e in exploits)
            open_ports = scan_ports(last_scan) if last_scan else []
            not_enumed = [p for p in open_ports if p not in enum_ports]
            if not shell and len(enum_ports) < MIN_ENUM_BEFORE_FINISH and not_enumed:
                print(f"    > finish blocked ({len(enum_ports)}/{MIN_ENUM_BEFORE_FINISH} services enumerated)")
                messages.append({"role": "user", "content":
                    f"Not enough reconnaissance to conclude: {len(enum_ports)} service(s) enumerated, "
                    f"aim for at least {MIN_ENUM_BEFORE_FINISH}. Open ports not yet enumerated: "
                    f"{', '.join(not_enumed[:8])}. Use enum on one of them (or exploit) before finishing."})
                stuck += 1
                continue
            corpus = "\n".join(seen)
            findings = scrub_unverified_cves(as_text(action.get("report")), corpus)
            services = parse_services(last_scan) if last_scan else []
            report = build_report(target, services, exploits, postexploit, findings)
            print("\n" + report)
            print(f"[*] report saved to {save_report(target, report)}")
            return
        elif kind == "error":
            print(f"[!] {as_text(action.get('thought'))}", file=sys.stderr)
            return
        else:
            valid = ", ".join(list(TOOLS) + (["exploit"] if exploit_enabled else []) + ["finish"])
            print(f"    > invalid action, re-prompting: {kind}")
            messages.append({"role": "user", "content":
                f"Invalid action. The 'action' field must be exactly one keyword from: {valid}. "
                f"Do not put a sentence there. Reply with one JSON object."})
            stuck += 1
            continue

    print("\n[!] max steps reached without a final report", file=sys.stderr)


def save_report(target, report, directory="reports"):
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{target}_{datetime.now():%Y-%m-%d_%H%M%S}.md")
    with open(path, "w") as f:
        f.write(report)
    return path


def main():
    parser = argparse.ArgumentParser(
        prog="agent", description="Autonomous pentest agent — the LLM drives, scope is enforced."
    )
    parser.add_argument("target", help="target IP to assess (must be in scope)")
    parser.add_argument("-s", "--scope", default="scope.txt", help="scope file (default: scope.txt)")
    parser.add_argument(
        "-H", "--host",
        default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        help="Ollama server URL (default: $OLLAMA_HOST or localhost)",
    )
    parser.add_argument("-m", "--model", default="qwen3:8b", help="model name")
    parser.add_argument("--max-steps", type=int, default=8, help="max reasoning steps")
    parser.add_argument("--exploit", action="store_true", help="enable exploitation of known lab vulns (off by default)")
    parser.add_argument("-y", "--yes", action="store_true",
                        help="auto-approve everything; never pause for confirmation or hints")
    parser.add_argument("--think", action="store_true",
                        help="enable the model's internal reasoning (slower; richer thoughts on qwen3)")
    parser.add_argument("--shell", action="store_true",
                        help="after a successful exploit, hand an interactive root shell to the human (interactive only)")
    args = parser.parse_args()

    problems = preflight(args.host, args.scope)
    if problems:
        for p in problems:
            print(f"[!] {p}", file=sys.stderr)
        sys.exit(1)

    interactive = sys.stdin.isatty() and not args.yes
    start = time.monotonic()
    run_mission(args.host, args.model, args.scope, args.target, args.max_steps, args.exploit, interactive, args.think, args.shell)
    print(f"[*] total time: {time.monotonic() - start:.1f}s")


if __name__ == "__main__":
    main()
