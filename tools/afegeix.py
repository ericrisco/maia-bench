#!/usr/bin/env python3
"""Afegeix UNA entrada al dataset: bloqueja, valida, fa commit i push.

Ús:  python3 tools/afegeix.py coneixement/<subtema>.jsonl <fitxer-amb-un-objecte-json>

Si la validació falla, desfà l'afegit i imprimeix els errors (codi de sortida 1).
Un sol candau compartit (a la carpeta git comuna) serialitza tots els processos que
escriuen alhora al mateix repositori.
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


def agafa_candau(path, espera=900):
    inici = time.time()
    while True:
        try:
            os.mkdir(path)
            return
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(path) > 600:  # candau orfe
                    os.rmdir(path)
                    continue
            except OSError:
                pass
            if time.time() - inici > espera:
                sys.exit("no s'ha pogut agafar el candau")
            time.sleep(2)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    fitxer, entrada = sys.argv[1], sys.argv[2]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    common = run("git", "rev-parse", "--git-common-dir", cwd=repo).stdout.strip()
    common = os.path.normpath(os.path.join(repo, common))
    candau = os.path.join(common, "maia-bench.lock")

    with open(entrada, encoding="utf-8") as f:
        r = json.loads(f.read())
    if not isinstance(r, dict):
        sys.exit("el fitxer ha de contenir un sol objecte JSON")
    linia = json.dumps(r, ensure_ascii=False) + "\n"

    ruta = os.path.join(repo, fitxer)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    agafa_candau(candau)
    try:
        abans = open(ruta, "rb").read() if os.path.exists(ruta) else None
        with open(ruta, "ab") as f:
            if abans and not abans.endswith(b"\n"):
                f.write(b"\n")
            f.write(linia.encode("utf-8"))

        v = run(sys.executable, os.path.join(repo, "tools", "valida.py"), fitxer, cwd=repo)
        if v.returncode != 0:
            if abans is None:
                os.remove(ruta)
            else:
                open(ruta, "wb").write(abans)
            print(v.stdout + v.stderr)
            sys.exit(1)

        run("git", "add", "--", fitxer, cwd=repo)
        msg = f"{GITMOJI} data({r['id']}): {' '.join(str(r['pregunta']).split())[:180]}"
        c = run("git", "commit", "-q", "-m", msg, "--", fitxer, cwd=repo)
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
        print("el push ha fallat 4 cops:\n" + p.stderr)
        sys.exit(1)
    finally:
        shutil.rmtree(candau, ignore_errors=True)


if __name__ == "__main__":
    main()
