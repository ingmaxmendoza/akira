#!/usr/bin/env python3
"""Offload a prompt to LM Studio. Usage:
  python lm.py "your prompt"
  cat file.md | python lm.py "summarize this:"
"""
import json, sys, urllib.request

URL = "http://localhost:1234/v1/chat/completions"
MODEL = ""  # empty = auto-pick first loaded chat model

def pick_model():
    with urllib.request.urlopen("http://localhost:1234/v1/models", timeout=10) as r:
        ids = [m["id"] for m in json.load(r)["data"]]
    return next(i for i in ids if "embed" not in i)

def ask(prompt, system=None):
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    body = json.dumps({"model": MODEL or pick_model(), "messages": messages, "temperature": 0.2}).encode()
    req = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
    # ponytail: no retries/streaming; add if long generations time out
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["choices"][0]["message"]["content"]

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:])
    if not sys.stdin.isatty():  # piped input gets appended
        prompt += "\n\n" + sys.stdin.read()
    if not prompt.strip():
        sys.exit(__doc__)
    print(ask(prompt))
