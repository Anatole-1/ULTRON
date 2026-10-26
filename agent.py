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

import requests

from nmap_tool import run_nmap
from enum_tool import run_enum

SYSTEM_PROMPT = """You are an autonomous penetration-testing agent operating in an authorized lab.
You choose one action at a time; an external executor runs it and returns the result.

Tools available:
- nmap: broad service/version scan of a target IP.
- enum: deeper scan of ONE port on the target (runs nmap vulnerability scripts).

Reply with ONE JSON object and nothing else:
  {"thought": "...", "action": "nmap"|"enum"|"finish", "target": "<ip>", "port": "<port>", "report": "<findings>"}

Rules:
- Start with nmap. Then use enum on the most interesting or outdated service to
  look for known vulnerabilities. Finish once you have enough.
- Base every statement strictly on the observations returned to you. Never mention
  a port, service, version, or vulnerability that is not present in an observation.
- Do not repeat an action you have already performed.
- Stay factual and terse: no greetings, no first person, no speculation.
- For "finish", the "report" field contains exactly these two lines:
  Notable findings: <outdated/risky services and any vulnerabilities found by enum>
  Next steps: <concrete follow-up actions>
  (The target and the full list of open services are added automatically — do not include them.)"""


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


def run_mission(host, model, scope_file, target, max_steps):
    print(f"[*] target {target} | brain {model} @ {host}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Assess target {target}. Decide the first action."},
    ]
    done = set()
    last_scan = None

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
        elif kind == "finish":
            report = as_text(action.get("report"))
            services = parse_services(last_scan) if last_scan else []
            print("\n=== REPORT ===")
            print(f"Target: {target}")
            print("Open services: " + (", ".join(services) if services else "(no nmap scan completed)"))
            print(report if report else "[!] model returned an empty report")
            return
        elif kind == "error":
            print(f"[!] {as_text(action.get('thought'))}", file=sys.stderr)
            return
        else:
            print(f"[!] unexpected action from model: {kind}", file=sys.stderr)
            return

    print("\n[!] max steps reached without a final report", file=sys.stderr)


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
    args = parser.parse_args()

    problems = preflight(args.host, args.scope)
    if problems:
        for p in problems:
            print(f"[!] {p}", file=sys.stderr)
        sys.exit(1)

    run_mission(args.host, args.model, args.scope, args.target, args.max_steps)


if __name__ == "__main__":
    main()
