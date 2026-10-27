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
from datetime import datetime

import requests

from nmap_tool import run_nmap
from enum_tool import run_enum
from exploit_tool import run_exploit, MODULES


def build_prompt(exploit_enabled):
    tools = [
        "- nmap: broad service/version scan of a target IP.",
        "- enum: deeper scan of ONE port on the target (runs nmap vulnerability scripts).",
    ]
    fields = '"thought": "...", "action": "nmap"|"enum"|"finish", "target": "<ip>", "port": "<port>"'
    exploit_rule = ""
    if exploit_enabled:
        modules = ", ".join(f"{k} ({v['desc']})" for k, v in MODULES.items())
        tools.append(f"- exploit: launch a known exploit module against the target. Allowed modules: {modules}.")
        fields = fields.replace('"finish"', '"exploit"|"finish"') + ', "module": "<module key>"'
        exploit_rule = ("- When a scan shows a service matching an allowed exploit module, use "
                        "'exploit' with that module key to confirm the vulnerability.\n"
                        "- If an exploit returns no session, try a different allowed module before giving up.\n")
    fields += ', "report": "<findings>"'
    tool_list = "\n".join(tools)
    return (
        "You are an autonomous penetration-testing agent operating in an authorized lab.\n"
        "You choose one action at a time; an external executor runs it and returns the result.\n\n"
        f"Tools available:\n{tool_list}\n\n"
        "Reply with ONE JSON object and nothing else:\n"
        f"  {{{fields}}}\n\n"
        "Rules:\n"
        "- The 'action' field must be EXACTLY one keyword (nmap, enum, exploit, finish). Never put a sentence there.\n"
        "- Start with nmap. Then use enum on the most interesting or outdated service.\n"
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


def build_report(target, services, exploits, findings):
    service_lines = "\n".join(f"- {s}" for s in services) if services else "- (no nmap scan completed)"
    exploit_lines = "\n".join(f"- {e}" for e in exploits) if exploits else "- (none attempted)"
    return (
        f"# Pentest report - {target}\n\n"
        f"_Generated {datetime.now():%Y-%m-%d %H:%M}_\n\n"
        f"## Open services\n{service_lines}\n\n"
        f"## Exploitation\n{exploit_lines}\n\n"
        f"## Analysis\n{findings if findings else '(model returned an empty report)'}\n"
    )


def ask_llm(host, model, messages):
    payload = {"model": model, "messages": messages, "stream": False, "format": "json"}
    error = "unknown error"
    for _ in range(2):
        try:
            resp = requests.post(f"{host}/api/chat", json=payload, timeout=120)
            resp.raise_for_status()
            data = json.loads(resp.json()["message"]["content"])
            return data if isinstance(data, dict) else {"action": "error", "thought": "model returned non-object JSON"}
        except requests.exceptions.RequestException as e:
            error = f"cannot reach the model server: {e}"
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


def run_mission(host, model, scope_file, target, max_steps, exploit_enabled):
    print(f"[*] target {target} | brain {model} @ {host}" + (" | exploit ON" if exploit_enabled else ""))
    messages = [
        {"role": "system", "content": build_prompt(exploit_enabled)},
        {"role": "user", "content": f"Assess target {target}. Decide the first action."},
    ]
    done = set()
    last_scan = None
    exploits = []

    for step in range(1, max_steps + 1):
        action = ask_llm(host, model, messages)
        messages.append({"role": "assistant", "content": json.dumps(action)})
        print(f"\n[{step}] {as_text(action.get('thought'))}")

        kind = action.get("action")
        if kind == "nmap":
            scan_target = as_text(action.get("target"))
            if ("nmap", scan_target) in done:
                print(f"    > skip (already scanned {scan_target})")
                messages.append({"role": "user", "content":
                    f"Already scanned {scan_target}. Do not repeat it; use the result or finish."})
                continue
            print(f"    > nmap {scan_target}")
            output = run_nmap(scan_target, scope_file)
            if output is not None:
                done.add(("nmap", scan_target))
                last_scan = output
                observation = truncate(output)
            else:
                observation = f"REFUSED or invalid: {scan_target} is not in scope."
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        elif kind == "enum":
            scan_target = as_text(action.get("target"))
            port = as_text(action.get("port"))
            if not port:
                messages.append({"role": "user", "content": "Observation: enum requires a port."})
                continue
            if ("enum", scan_target, port) in done:
                print(f"    > skip (already enumerated {scan_target}:{port})")
                messages.append({"role": "user", "content":
                    f"Already enumerated {scan_target}:{port}. Use the result or finish."})
                continue
            print(f"    > enum {scan_target}:{port}")
            output = run_enum(scan_target, port, scope_file)
            if output is not None:
                done.add(("enum", scan_target, port))
                observation = truncate(output)
            else:
                observation = f"REFUSED or invalid: {scan_target}:{port}."
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        elif kind == "exploit":
            scan_target = as_text(action.get("target"))
            module_key = as_text(action.get("module"))
            if not exploit_enabled:
                messages.append({"role": "user", "content": "Observation: exploitation is disabled (run with --exploit)."})
                continue
            if ("exploit", scan_target, module_key) in done:
                print(f"    > skip (already tried {module_key} on {scan_target})")
                messages.append({"role": "user", "content":
                    f"Already tried {module_key} on {scan_target}. Use the result or finish."})
                continue
            print(f"    > exploit {module_key} on {scan_target}")
            output = run_exploit(scan_target, module_key, scope_file)
            if output is None:
                observation = f"REFUSED or unknown module/target: {module_key} on {scan_target}."
            else:
                done.add(("exploit", scan_target, module_key))
                outcome = exploit_result(output)
                exploits.append(f"{module_key} on {scan_target} -> {outcome}")
                observation = truncate(output)
                if outcome == "no session":
                    tried = {e[2] for e in done if e[0] == "exploit"}
                    remaining = [k for k in MODULES if k not in tried]
                    if remaining:
                        observation += ("\n\n[note] No shell obtained with this module. "
                                        f"Untried exploit modules: {', '.join(remaining)}. "
                                        "Try one that matches an open service before finishing.")
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        elif kind == "finish":
            findings = as_text(action.get("report"))
            services = parse_services(last_scan) if last_scan else []
            report = build_report(target, services, exploits, findings)
            print("\n" + report)
            print(f"[*] report saved to {save_report(target, report)}")
            return
        elif kind == "error":
            print(f"[!] {as_text(action.get('thought'))}", file=sys.stderr)
            return
        else:
            valid = "nmap, enum, exploit, finish" if exploit_enabled else "nmap, enum, finish"
            print(f"    > invalid action, re-prompting: {kind}")
            messages.append({"role": "user", "content":
                f"Invalid action. The 'action' field must be exactly one keyword from: {valid}. "
                f"Do not put a sentence there. Reply with one JSON object."})
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
    parser.add_argument("-m", "--model", default="qwen2.5:7b", help="model name")
    parser.add_argument("--max-steps", type=int, default=8, help="max reasoning steps")
    parser.add_argument("--exploit", action="store_true", help="enable exploitation of known lab vulns (off by default)")
    args = parser.parse_args()

    problems = preflight(args.host, args.scope)
    if problems:
        for p in problems:
            print(f"[!] {p}", file=sys.stderr)
        sys.exit(1)

    run_mission(args.host, args.model, args.scope, args.target, args.max_steps, args.exploit)


if __name__ == "__main__":
    main()
