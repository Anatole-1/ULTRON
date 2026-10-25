"""Autonomous pentest agent (ReAct loop).

The LLM chooses each action; this orchestrator runs it through the
scope-enforced tools and feeds the result back, until a final report.
"""

import argparse
import json
import os
import sys

import requests

from nmap_tool import run_nmap

SYSTEM_PROMPT = """You are an autonomous penetration-testing agent operating in an authorized lab.
You choose one action at a time; an external executor runs it and returns the result.

Tool available:
- nmap: service/version scan of a target IP.

Reply with ONE JSON object and nothing else:
  {"thought": "...", "action": "nmap"|"finish", "target": "<ip>", "report": "<findings>"}

Rules:
- Base every statement strictly on the observations returned to you. Never mention
  a port, service, or version that is not present in an observation.
- Do not repeat an action you have already performed. Once you have the scan
  results, move to "finish".
- Stay factual and terse: no greetings, no first person, no speculation.
- The report uses these four lines, each starting with its label:
  Target: <ip>
  Open services: <port/service/version, comma-separated>
  Notable findings: <outdated or risky services>
  Next steps: <concrete follow-up actions>"""


def ask_llm(host, model, messages):
    resp = requests.post(
        f"{host}/api/chat",
        json={"model": model, "messages": messages, "stream": False, "format": "json"},
        timeout=180,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["message"]["content"])


def run_mission(host, model, scope_file, target, max_steps):
    print(f"[*] target {target} | brain {model} @ {host}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Assess target {target}. Decide the first action."},
    ]
    done = set()

    for step in range(1, max_steps + 1):
        action = ask_llm(host, model, messages)
        messages.append({"role": "assistant", "content": json.dumps(action)})
        print(f"\n[{step}] {action.get('thought', '').strip()}")

        kind = action.get("action")
        if kind == "nmap":
            scan_target = action.get("target", "")
            if ("nmap", scan_target) in done:
                print(f"    > skip (already scanned {scan_target})")
                messages.append({"role": "user", "content":
                    f"Already scanned {scan_target}. Do not repeat it; use the result or finish."})
                continue
            print(f"    > nmap {scan_target}")
            output = run_nmap(scan_target, scope_file)
            if output is None:
                observation = f"REFUSED: {scan_target} is out of scope."
            else:
                observation = output
                done.add(("nmap", scan_target))
            messages.append({"role": "user", "content": f"Observation:\n{observation}"})
        elif kind == "finish":
            print("\n=== REPORT ===")
            print(action.get("report", "").strip())
            return
        else:
            print(f"[!] unknown action: {kind}", file=sys.stderr)
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
    parser.add_argument("--max-steps", type=int, default=6, help="max reasoning steps")
    args = parser.parse_args()

    run_mission(args.host, args.model, args.scope, args.target, args.max_steps)


if __name__ == "__main__":
    main()
