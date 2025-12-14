#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import datetime

# ==========================================================
# CONFIGURATION
# ==========================================================
DEFAULT_MODEL = "gpt-4o-mini"   # Change to e.g. "gemini/gemini-2.5-flash"
DEBUG_AI = True                 # Prints stderr from llm if True

# ==========================================================
# COLORS
# ==========================================================
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

def say(msg): print(f"{GREEN}{msg}{RESET}")
def warn(msg): print(f"{YELLOW}{msg}{RESET}")
def err(msg): print(f"{RED}{msg}{RESET}", file=sys.stderr)

# ==========================================================
# HELPERS
# ==========================================================
def run(cmd, capture=False, env=None):
    if capture:
        return subprocess.check_output(cmd, shell=True, text=True, env=env).strip()
    subprocess.check_call(cmd, shell=True, env=env)

def safe(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except:
        return ""

def has_commits():
    return safe("git rev-parse --verify HEAD") != ""

def semantic(tag):
    m = re.match(r"^v([0-9]+)\.([0-9]+)\.([0-9]+)$", tag)
    return tuple(map(int, m.groups())) if m else None

def truncate_summary(s, limit=80):
    s = s.strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut + "…"

def ensure_identity():
    name = safe("git config --global user.name")
    email = safe("git config --global user.email")

    if name and email:
        return name, email

    warn("⚠️ Git identity not set. Required before committing.")
    name = input("Enter author name: ").strip()
    email = input("Enter author email: ").strip()

    if not name or not email:
        err("❌ Both name and email are required.")
        sys.exit(4)

    save = input("Save identity globally? (y/N): ").strip().lower()
    if save == "y":
        run(f'git config --global user.name "{name}"')
        run(f'git config --global user.email "{email}"')
        say("💾 Saved Git global identity.")

    return name, email

# ==========================================================
# AI COMMIT MESSAGE HANDLER
# ==========================================================
def generate_ai_commit_message(model, diff):
    prompt = f"""
You are a precise engineer. Follow the required format.

Output EXACTLY in this structure:

<One-line summary (<120 chars)>

### Changes
- concise bullet
- concise bullet

### Rationale
Sentence explaining intent OR:
Rationale: Not assessable from diff.

NEVER include file names.
NEVER fabricate information.

Diff:
{diff}
"""

    try:
        proc = subprocess.Popen(
            ["llm", "-m", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, errout = proc.communicate(prompt, timeout=25)

        if DEBUG_AI and errout:
            warn(f"[AI stderr] {errout}")

        if not out or len(out.strip()) < 10:
            warn("⚠️ AI returned empty or too-small output.")
            return None

        # Detect generic refusal text from Gemini Mini
        lower = out.lower()
        if "what would you like me to" in lower or "please provide me" in lower:
            warn("⚠️ Model refused structured prompt.")
            return None

        return out.strip()

    except subprocess.TimeoutExpired:
        warn("⚠️ AI timeout.")
        return None
    except Exception as e:
        warn(f"⚠️ AI failure: {e}")
        return None

# ==========================================================
# START — MUST BE INSIDE A REPO
# ==========================================================
inside = safe("git rev-parse --is-inside-work-tree")
if inside != "true":
    err("❌ Not inside a Git repository.")
    sys.exit(1)

# ==========================================================
# BOOTSTRAP — NO COMMITS
# ==========================================================
if not has_commits():
    warn("⚠️ No commits found — bootstrapping repository.")

    author_name, author_email = ensure_identity()

    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_NAME"] = author_name
    env["GIT_COMMITTER_EMAIL"] = author_email

    run("git add .")
    subprocess.check_call(["git", "commit", "-m", "Initial commit"], env=env)

    warn("🏷️ Creating initial tag v0.1.0")
    run('git tag -a v0.1.0 -m "Initial version tag"')

    branch = safe("git rev-parse --abbrev-ref HEAD") or "main"
    run(f"git push -u origin {branch}")
    run("git push origin v0.1.0")

    last_tag = "v0.1.0"
else:
    last_tag = safe("git describe --tags --abbrev=0")
    if not last_tag:
        warn("⚠️ No tags found — creating v0.1.0")
        run('git tag -a v0.1.0 -m "Initial version tag"')
        run("git push origin v0.1.0")
        last_tag = "v0.1.0"

# ==========================================================
# VERSION MATH
# ==========================================================
sem = semantic(last_tag)
if not sem:
    err(f"❌ Existing tag {last_tag} is not semantic.")
    sys.exit(2)

major, minor, patch = sem
next_version = f"v{major}.{minor}.{patch+1}"

# ==========================================================
# STAGE + DIFF
# ==========================================================
run("git add .")
changed = safe("git diff --cached --name-only")
if not changed:
    err("❌ No staged changes.")
    sys.exit(3)

diff = safe("git diff --cached --unified=0")
if len(diff) > 18000:
    diff = diff[:18000] + "\n...\n[diff truncated]"

# ==========================================================
# MODEL SELECTION (User Override)
# ==========================================================
print(f"{MAGENTA}Available model:{RESET} {DEFAULT_MODEL}")
model_choice = input(f"{YELLOW}Enter model or leave empty for default:{RESET} ").strip()
model = model_choice if model_choice else DEFAULT_MODEL

# ==========================================================
# AI COMMIT MESSAGE
# ==========================================================
print(f"{CYAN}🤖 Generating commit message using {model}...{RESET}")

commit_msg = generate_ai_commit_message(model, diff)

# Retry once with fallback
if commit_msg is None:
    warn("Retrying with simplified prompt...")
    commit_msg = generate_ai_commit_message(model, "CHANGES:\n" + diff[:5000])

if commit_msg is None:
    warn("AI unavailable. Falling back to manual commit message.")
    commit_msg = input("Enter commit message: ").strip() or "update"

summary = commit_msg.split("\n")[0].strip() or "update"
title = truncate_summary(summary)

# ==========================================================
# FINAL COMMIT MESSAGE BUILD
# ==========================================================
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

final_msg = f"""Version: {next_version} — {title}
Timestamp: {timestamp}

{commit_msg}
"""

# ==========================================================
# AUTHOR IDENTITY
# ==========================================================
author_name, author_email = ensure_identity()

env = os.environ.copy()
env["GIT_AUTHOR_NAME"] = author_name
env["GIT_AUTHOR_EMAIL"] = author_email
env["GIT_COMMITTER_NAME"] = author_name
env["GIT_COMMITTER_EMAIL"] = author_email

# ==========================================================
# WRITE COMMIT, TAG, PUSH
# ==========================================================
subprocess.check_call(["git", "commit", "-m", final_msg], env=env)

run(f'git tag -a {next_version} -m "{final_msg}"')

branch = safe("git rev-parse --abbrev-ref HEAD") or "main"
run(f"git push -u origin {branch}")
run(f"git push origin {next_version}")

say(f"🎉 Released {next_version} with model {model}!")
