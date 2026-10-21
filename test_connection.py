#!/usr/bin/env python3
"""
Minimal connectivity test: send one prompt to the Ollama server (the "brain")
and print its answer. First building block of the autonomous agent: the
communication pipe between K (the hands) and F (the brain).
"""

import os
import sys
import requests

# Ollama server address, read from an environment variable so the real
# infrastructure IP is never hardcoded in this (soon public) repository.
# On K:  export OLLAMA_HOST="http://<server-ip>:11434"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL = "qwen2.5:7b"


def ask(prompt):
    """Send a prompt to Ollama and return the model's text answer."""
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,  # get the full answer at once (simpler to start)
    }
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["response"]


def main():
    print(f"[*] Ollama server: {OLLAMA_HOST}")
    print(f"[*] Model: {MODEL}\n")

    prompt = "In one sentence, what is a penetration test?"
    try:
        answer = ask(prompt)
    except requests.exceptions.ConnectionError:
        print("[!] Could not reach the Ollama server.")
        print("    Is F on? Is Ollama running? Is OLLAMA_HOST set correctly?")
        sys.exit(1)

    print("[+] Answer from the brain:")
    print(answer)


if __name__ == "__main__":
    main()
