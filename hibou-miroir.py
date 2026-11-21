#!/usr/bin/env python3
"""hibou-miroir — prépare (machine connectée) puis importe (forge, hors ligne) des dépendances dans Forgejo.

  hibou-miroir.py prepare --src bundle/miroir.d --out bundle/mirror
  hibou-miroir.py push    --dir /m --url http://forgejo:3000 --owner hibou \
                          --user <admin> --password XXX --token YYY --registry forge.hibou.lan

prepare : paquets Python téléchargés dans des conteneurs python:<version>-slim (HIBOU_PY_VERSIONS,
          ex. « 3.11 3.12 3.13 ») pour avoir les bonnes roues ; npm par Docker si npm est absent.
push    : lancé dans l’image hibou/miroir sur forge (twine, npm, git, client Docker).

Listes lues dans --src (une entrée par ligne, '#' = commentaire) :
  requirements.txt    paquets Python (syntaxe pip)           -> registre PyPI de Forgejo
  npm-packages.txt    paquets npm (nom ou nom@version)      -> registre npm de Forgejo
  git-repos.txt       URLs de dépôts git                     -> dépôts Forgejo (créés par l’API, puis push)
  docker-images.txt   images Docker (nom:tag)                -> registre de conteneurs de Forgejo

--dry-run : affiche ce qui serait fait sans rien exécuter ni télécharger.
"""
import argparse, base64, hashlib, json, os, re, shlex, shutil, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- utilitaires
def log(msg): print(f"[hibou mirror] {msg}", flush=True)

def read_list(path):
    p = Path(path)
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out

SECRETS = set()

def redact(text):
    for s in SECRETS:
        if s:
            text = text.replace(s, "***")
    return text

def run(cmd, dry, cwd=None, env=None, check=True, capture=False):
    log("$ " + redact(" ".join(shlex.quote(str(c)) for c in cmd)))
    if dry:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, check=check,
                          text=True, capture_output=capture)

def docker_cmd():
    return shlex.split(os.environ.get("HIBOU_DOCKER", "docker"))

def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")

def semver_key(v):
    """Clé de tri simple : les versions finales passent après leurs pré-versions."""
    core, _, pre = v.partition("-")
    core = core.split("+", 1)[0]
    nums = tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.]", core))
    nums = nums + (0,) * (4 - len(nums))
    return (nums, 1 if not pre else 0, pre)

def is_prerelease(v):
    return "-" in v.split("+", 1)[0]

# --------------------------------------------------------------------------- npm
def parse_npm_lock(lock):
    """package-lock.json (v2/v3) -> [{name, version, resolved, integrity}] dédupliqué."""
    seen, out = set(), []
    for key, meta in (lock.get("packages") or {}).items():
        if not key or "node_modules/" not in key:
            continue
        resolved = meta.get("resolved")
        if not resolved or not resolved.startswith("http"):
            continue
        name = key.rsplit("node_modules/", 1)[1]
        ver = meta.get("version")
        if not ver or (name, ver) in seen:
            continue
        seen.add((name, ver))
        out.append({"name": name, "version": ver, "resolved": resolved,
                    "integrity": meta.get("integrity", "")})
    return sorted(out, key=lambda e: (e["name"], semver_key(e["version"])))

def check_integrity(data, integrity):
    if not integrity:
        return True
    algo, _, b64 = integrity.partition("-")
    if algo not in ("sha512", "sha384", "sha256", "sha1"):
        return True
    return base64.b64encode(hashlib.new(algo, data).digest()).decode() == b64

# --------------------------------------------------------------------------- prepare
def prepare(a):
    src, out, dry = Path(a.src), Path(a.out), a.dry_run
    out.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else {"pypi", "npm", "git", "images"}

    reqs = read_list(src / "requirements.txt")
    npms = read_list(src / "npm-packages.txt")
    gits = read_list(src / "git-repos.txt")
    imgs = read_list(src / "docker-images.txt")
    log(f"listes : pypi={len(reqs)} npm={len(npms)} git={len(gits)} images={len(imgs)}")

    if reqs and "pypi" in only:
        d = out / "pypi"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        tmp = out / "_requirements.txt"; tmp.write_text("\n".join(reqs) + "\n")
        versions = os.environ.get("HIBOU_PY_VERSIONS", "").split()
        if versions:
            # Une passe par version de Python : roues compilées (cp311, cp312…) pour chacune.
            for v in versions:
                run([*docker_cmd(), "run", "--rm", "-v", f"{d.resolve()}:/out", "-v", f"{tmp.resolve()}:/req.txt:ro",
                     f"python:{v}-slim", "pip", "download", "-q", "--disable-pip-version-check", "-r", "/req.txt", "-d", "/out"], dry)
        else:
            run([sys.executable, "-m", "pip", "download", "-r", tmp, "-d", d], dry)
        tmp.unlink(missing_ok=True)

    if npms and "npm" in only:
        d = out / "npm"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        work = out / "_npm_work"; shutil.rmtree(work, ignore_errors=True); work.mkdir(parents=True)
        (work / "package.json").write_text('{"name":"hibou mirror","version":"0.0.0","private":true}')
        npm = ["npm"] if shutil.which("npm") else [*docker_cmd(), "run", "--rm", "-v", f"{work.resolve()}:/w", "-w", "/w", "node:22-bookworm-slim", "npm"]
        run([*npm, "install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund", *npms], dry, cwd=work)
        entries = []
        if not dry:
            lock = json.loads((work / "package-lock.json").read_text())
            for e in parse_npm_lock(lock):
                fname = e["resolved"].rsplit("/", 1)[-1]
                dest = d / safe(e["name"]) / fname
                dest.parent.mkdir(parents=True, exist_ok=True)
                log(f"npm  {e['name']}@{e['version']}")
                data = urllib.request.urlopen(e["resolved"], timeout=120).read()
                if not check_integrity(data, e["integrity"]):
                    sys.exit(f"intégrité invalide : {e['name']}@{e['version']}")
                dest.write_bytes(data)
                entries.append({"name": e["name"], "version": e["version"], "file": str(dest.relative_to(out))})
            (d / "index.json").write_text(json.dumps(entries, indent=1))
            log(f"npm : {len(entries)} tarballs")
        shutil.rmtree(work, ignore_errors=True)

    if gits and "git" in only:
        d = out / "git"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        index = []
        for url in gits:
            name = safe(re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1]))
            dest = d / f"{name}.git"
            run(["git", "clone", "--mirror", url, dest], dry)
            index.append({"name": name, "dir": f"git/{name}.git", "origin": url})
        if not dry:
            (d / "index.json").write_text(json.dumps(index, indent=1))

    if imgs and "images" in only:
        d = out / "images"; shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True)
        index = []
        for img in imgs:
            f = d / (safe(img) + ".tar")
            run([*docker_cmd(), "pull", img], dry)
            run([*docker_cmd(), "save", "-o", f, img], dry)
            index.append({"image": img, "file": f"images/{f.name}"})
        if not dry:
            (d / "index.json").write_text(json.dumps(index, indent=1))
    log("préparation terminée")

# --------------------------------------------------------------------------- push
def target_image_ref(image, registry, owner):
    """ghcr.io/foo/bar:1.2 -> 127.0.0.1:3001/<owner>/foo-bar:1.2 ; ubuntu:24.04 -> .../ubuntu:24.04"""
    name, _, tag = image.rpartition(":") if re.search(r":[^/]+$", image) else (image, "", "latest")
    if not name:
        name, tag = image, "latest"
    parts = name.split("/")
    if len(parts) > 1 and ("." in parts[0] or ":" in parts[0] or parts[0] == "localhost"):
        parts = parts[1:]                      # retire le registre d'origine
    if parts and parts[0] == "library":
        parts = parts[1:]
    flat = "-".join(parts).lower()
    return f"{registry}/{owner}/{flat}:{tag}"

def push(a):
    d, dry = Path(a.dir), a.dry_run
    SECRETS.update({a.password, a.token})
    base = a.url.rstrip("/")
    only = set(a.only.split(",")) if a.only else {"pypi", "npm", "git", "images"}
    host_port = re.sub(r"^https?://", "", base)
    registry = a.registry or host_port

    # --- PyPI (twine dans un venv alimenté hors ligne depuis tools/)
    pyfiles = sorted(p for p in (d / "pypi").glob("*") if p.is_file()) if (d / "pypi").is_dir() else []
    if pyfiles and "pypi" in only:
        # Forgejo refuse --skip-existing : un envoi par fichier, 409 = déjà présent. Mot de passe par l’environnement.
        env = {**os.environ, "TWINE_USERNAME": a.user, "TWINE_PASSWORD": a.password}
        ok = skipped = 0
        for f in pyfiles:
            r = run([shutil.which("twine") or "twine", "upload", "--non-interactive",
                     "--repository-url", f"{base}/api/packages/{a.owner}/pypi", f], dry, env=env, check=False, capture=True)
            text = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                ok += 1
            elif re.search(r"409|Conflict|already exists", text, re.I):
                skipped += 1
            else:
                log(redact(f"pypi ÉCHEC {f.name}: {text.strip()[-300:]}"))
        log(f"pypi : {ok} publiés, {skipped} déjà présents")

    # --- npm (npm publish de chaque tarball, versions croissantes => dist-tag latest = la plus récente)
    idx = d / "npm" / "index.json"
    if idx.is_file() and "npm" in only:
        entries = json.loads(idx.read_text())
        entries.sort(key=lambda e: (e["name"], semver_key(e["version"])))
        npmrc = Path(a.tmpdir or "/tmp") / "hibou-npmrc"
        reg = f"{base}/api/packages/{a.owner}/npm/"
        npmrc.write_text(f"registry={reg}\n//{host_port}/api/packages/{a.owner}/npm/:_authToken={a.token}\n")
        os.chmod(npmrc, 0o600)
        ok = skipped = 0
        for e in entries:
            tag = "prerelease" if is_prerelease(e["version"]) else "latest"
            r = run(["npm", "publish", d / e["file"], "--userconfig", npmrc, "--registry", reg, "--tag", tag],
                    dry, check=False, capture=True)
            text = (r.stdout or "") + (r.stderr or "")
            if r.returncode == 0:
                ok += 1
            elif re.search(r"409|Conflict|previously published|already exists", text, re.I):
                skipped += 1
            else:
                log(redact(f"npm ÉCHEC {e['name']}@{e['version']}: {text.strip()[-300:]}"))
        npmrc.unlink(missing_ok=True)
        log(f"npm : {ok} publiés, {skipped} déjà présents")

    # --- git (branches + tags uniquement : Forgejo refuse les refs cachées type refs/pull/*)
    idx = d / "git" / "index.json"
    if idx.is_file() and "git" in only:
        for e in json.loads(idx.read_text()):
            remote = f"http://{a.user}:{a.token}@{host_port}/{a.owner}/{e['name']}.git"
            # Dépôt créé par l’API (409 : déjà là) : Forgejo n’accepte plus la création par push.
            if not dry:
                req = urllib.request.Request(f"{base}/api/v1/orgs/{a.owner}/repos", method="POST",
                                             data=json.dumps({"name": e["name"], "private": True}).encode(),
                                             headers={"Content-Type": "application/json", "Authorization": f"token {a.token}"})
                try:
                    urllib.request.urlopen(req, timeout=60)
                except urllib.error.HTTPError as x:
                    if x.code != 409:
                        log(f"git ÉCHEC création de {a.owner}/{e['name']} : HTTP {x.code}")
            # Conteneur root, dépôt monté appartenant à l’utilisateur du bundle : git exige safe.directory.
            run(["git", "-c", f"safe.directory={(d / e['dir']).resolve()}", "-C", d / e["dir"], "-c", "credential.helper=", "push", "--prune", remote,
                 "+refs/heads/*:refs/heads/*", "+refs/tags/*:refs/tags/*"], dry)

    # --- images Docker -> registre de conteneurs
    idx = d / "images" / "index.json"
    if idx.is_file() and "images" in only:
        dk = docker_cmd()
        if not dry:
            subprocess.run([*dk, "login", registry, "-u", a.user, "--password-stdin"],
                           input=a.password, text=True, check=True)
        else:
            log(f"$ docker login {registry} -u {a.user} --password-stdin")
        for e in json.loads(idx.read_text()):
            ref = target_image_ref(e["image"], registry, a.owner)
            run([*dk, "load", "-i", d / e["file"]], dry)
            run([*dk, "tag", e["image"], ref], dry)
            run([*dk, "push", ref], dry)
            log(f"image publiée : {ref}")
    log("import terminé")

# --------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="Hibou : miroir de dépendances via Forgejo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare"); p.add_argument("--src", required=True); p.add_argument("--out", required=True)
    p.add_argument("--only"); p.add_argument("--dry-run", action="store_true"); p.set_defaults(fn=prepare)

    q = sub.add_parser("push"); q.add_argument("--dir", required=True); q.add_argument("--url", required=True)
    q.add_argument("--owner", required=True); q.add_argument("--user", required=True)
    q.add_argument("--password", required=True); q.add_argument("--token", required=True)
    q.add_argument("--registry")
    q.add_argument("--tmpdir"); q.add_argument("--only"); q.add_argument("--dry-run", action="store_true")
    q.set_defaults(fn=push)

    a = ap.parse_args()
    try:
        a.fn(a)
    except subprocess.CalledProcessError as e:   # sans la ligne de commande brute : elle peut contenir un jeton
        log(redact(f"ÉCHEC ({e.returncode}) : {' '.join(str(c) for c in e.cmd)}")); sys.exit(1)

if __name__ == "__main__":
    main()
