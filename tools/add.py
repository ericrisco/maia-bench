#!/usr/bin/env python3
"""Adds ONE entry to the dataset: locks, validates, commits and pushes.

Usage:  python3 tools/add.py knowledge/<subtopic>.jsonl <file-with-one-json-object>

If validation fails, it undoes the addition and prints the errors (exit code 1).
A single shared lock (in the common git folder) serialises every process writing to the same repository at once.
"""
import json
import os
import shutil
import subprocess
import sys
import time

GITMOJI = "✨"


def run(*cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def take_lock(path, wait=900):
    start = time.time()
    while True:
        try:
            os.mkdir(path)
            return
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(path) > 600:  # orphan lock
                    os.rmdir(path)
                    continue
            except OSError:
                pass
            if time.time() - start > wait:
                sys.exit("could not take the lock")
            time.sleep(2)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    file, entry = sys.argv[1], sys.argv[2]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    common = run("git", "rev-parse", "--git-common-dir", cwd=repo).stdout.strip()
    common = os.path.normpath(os.path.join(repo, common))
    lock = os.path.join(common, "maia-bench.lock")

    with open(entry, encoding="utf-8") as f:
        r = json.loads(f.read())
    if not isinstance(r, dict):
        sys.exit("the file must contain a single JSON object")
    line = json.dumps(r, ensure_ascii=False) + "\n"

    path = os.path.join(repo, file)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    take_lock(lock)
    try:
        before = open(path, "rb").read() if os.path.exists(path) else None
        with open(path, "ab") as f:
            if before and not before.endswith(b"\n"):
                f.write(b"\n")
            f.write(line.encode("utf-8"))

        v = run(sys.executable, os.path.join(repo, "tools", "validate.py"), file, cwd=repo)
        if v.returncode != 0:
            if before is None:
                os.remove(path)
            else:
                open(path, "wb").write(before)
            print(v.stdout + v.stderr)
            sys.exit(1)

        run("git", "add", "--", file, cwd=repo)
        msg = f"{GITMOJI} data({r['id']}): {' '.join(str(r['question']).split())[:180]}"
        c = run("git", "commit", "-q", "-m", msg, "--", file, cwd=repo)
        if c.returncode != 0:
            print(c.stdout + c.stderr)
            sys.exit(1)
        for _ in range(4):
            p = run("git", "push", "-q", "origin", "HEAD:dataset", cwd=repo)
            if p.returncode == 0:
                print(f"OK {r['id']}")
                return
            run("git", "pull", "-q", "--rebase", "origin", "dataset", cwd=repo)
            time.sleep(1)
        print("push failed 4 times:\n" + p.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(lock, ignore_errors=True)


if __name__ == "__main__":
    main()
