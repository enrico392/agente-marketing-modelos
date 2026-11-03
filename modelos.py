#!/usr/bin/env python3
"""Modelos da locução sem Hugging Face e sem login: cópia própria nos releases de um repositório público do GitHub.

  baixar   (máquina que renderiza, uma vez): baixa os arquivos do release, junta as partes, confere o SHA-256
           e guarda em LOCUCAO_MODELOS_RAIZ (padrão ~/locucao/modelos: chatterbox-mtl/ e whisper-small/). Depois tudo roda offline.
  espelhar (uma vez, dentro do GitHub Actions do seu repositório): baixa do Hugging Face os arquivos públicos
           do Chatterbox Multilingual e do Whisper small (sem token), divide o que passar de 1,9 GB e escreve manifesto.json.
           O workflow tools/espelho-modelos/espelhar.yml publica tudo como release.

Uso:
  python3 modelos.py baixar   [--repo dono/repositorio] [--tag chatterbox-mtl-v1] [--destino pasta]
  python3 modelos.py espelhar --saida pasta
  python3 modelos.py conferir [--destino pasta]
Repositório padrão: enrico392/agente-marketing-modelos (troque com LOCUCAO_MODELOS_REPO ou --repo).
Licença dos pesos: MIT (ResembleAI/chatterbox) — o LICENSE vai junto no release.
"""
import time
import argparse, hashlib, json, os, shutil, sys, urllib.request

CONJUNTOS = {  # pasta local -> (repositório público de origem, arquivos)
    "chatterbox-mtl": ("ResembleAI/chatterbox", ["ve.pt", "t3_mtl23ls_v2.safetensors", "s3gen.pt", "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json", "LICENSE"]),
    "whisper-small": ("Systran/faster-whisper-small", ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt", "README.md"]),
}
OPCIONAIS = {"LICENSE", "Cangjie5_TC.json", "README.md"}
PARTE = int(os.environ.get("LOCUCAO_PARTE", 1_900_000_000))  # releases do GitHub aceitam até 2 GB por arquivo
TAG = os.environ.get("LOCUCAO_MODELOS_TAG", "chatterbox-mtl-v1")
RAIZ = os.path.expanduser(os.environ.get("LOCUCAO_MODELOS_RAIZ", "~/locucao/modelos"))  # chatterbox-mtl/ e whisper-small/


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def baixar_url(url, dest, tentativas=8):
    """Baixa com retomada (Range): conexão que cai no meio continua de onde parou, até o tamanho bater."""
    tmp = dest + ".parcial"
    total = 0
    for t in range(tentativas):
        feito = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        hdr = {"User-Agent": "agente-marketing-locucao"}
        if feito:
            hdr["Range"] = f"bytes={feito}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=120) as r:
                if feito and r.status != 206:
                    feito = 0  # servidor ignorou o Range: recomeça
                if r.status == 206:
                    total = int((r.headers.get("Content-Range") or "/0").rsplit("/", 1)[1] or 0)
                else:
                    total = int(r.headers.get("Content-Length") or 0)
                with open(tmp, "ab" if feito else "wb") as f:
                    while True:
                        b = r.read(1 << 22)
                        if not b:
                            break
                        f.write(b); feito += len(b)
                        if total:
                            print(f"\r  {os.path.basename(dest)}: {feito * 100 // total}%", end="", file=sys.stderr)
        except Exception as e:
            print(f"\n  conexão caiu ({e}); retomando", file=sys.stderr)
        if total and os.path.getsize(tmp) >= total:
            break
        if not total and t > 0:
            break
        time.sleep(2 + t * 2)
    print(file=sys.stderr)
    if total and os.path.getsize(tmp) != total:
        sys.exit(f"{os.path.basename(dest)}: baixou {os.path.getsize(tmp)} de {total} bytes; rode de novo")
    os.replace(tmp, dest)


def espelhar(saida, origem=None):
    """Baixa os arquivos públicos (sem token) e prepara o release: nomes com prefixo da pasta, partes de até 1,9 GB."""
    os.makedirs(saida, exist_ok=True)
    man = {"licencas": {"chatterbox-mtl": "MIT (ResembleAI/chatterbox)", "whisper-small": "MIT (OpenAI Whisper, conversão Systran)"}, "arquivos": {}}
    for pasta, (repo, nomes) in CONJUNTOS.items():
        for nome in nomes:
            chave = f"{pasta}__{nome}"; dest = os.path.join(saida, chave)
            try:
                if origem:
                    shutil.copy(os.path.join(origem, pasta, nome), dest)
                else:
                    baixar_url(f"https://huggingface.co/{repo}/resolve/main/{nome}", dest)
            except Exception as e:
                if nome in OPCIONAIS:
                    print(f"aviso: {pasta}/{nome} não baixou ({e})", file=sys.stderr); continue
                raise
            tam = os.path.getsize(dest); info = {"pasta": pasta, "nome": nome, "sha256": sha256(dest), "tamanho": tam, "partes": []}
            if tam > PARTE:
                with open(dest, "rb") as f:
                    k = 0
                    while True:
                        b = f.read(PARTE)
                        if not b:
                            break
                        pn = f"{chave}.parte{k:02d}"; open(os.path.join(saida, pn), "wb").write(b); info["partes"].append(pn); k += 1
                os.remove(dest)
            man["arquivos"][chave] = info
    json.dump(man, open(os.path.join(saida, "manifesto.json"), "w"), indent=1)
    print(json.dumps({k: (v["tamanho"], len(v["partes"])) for k, v in man["arquivos"].items()}, indent=1))


def baixar(repo, tag, raiz):
    if not repo and not os.environ.get("LOCUCAO_MODELOS_BASE"):
        sys.exit("Informe o repositório: --repo dono/repositorio ou LOCUCAO_MODELOS_REPO.")
    base = os.environ.get("LOCUCAO_MODELOS_BASE") or f"https://github.com/{repo}/releases/download/{tag}"
    os.makedirs(raiz, exist_ok=True)
    baixar_url(f"{base}/manifesto.json", os.path.join(raiz, "manifesto.json"))
    man = json.load(open(os.path.join(raiz, "manifesto.json")))
    for chave, info in man["arquivos"].items():
        pasta = os.path.join(raiz, info["pasta"]); os.makedirs(pasta, exist_ok=True)
        final = os.path.join(pasta, info["nome"])
        if os.path.exists(final) and os.path.getsize(final) == info["tamanho"] and sha256(final) == info["sha256"]:
            print(f"  {info['pasta']}/{info['nome']}: já está ok", file=sys.stderr); continue
        if info["partes"]:
            with open(final + ".juntando", "wb") as out:
                for pn in info["partes"]:
                    pp = os.path.join(pasta, pn); baixar_url(f"{base}/{pn}", pp)
                    with open(pp, "rb") as f:
                        shutil.copyfileobj(f, out)
                    os.remove(pp)
            os.replace(final + ".juntando", final)
        else:
            baixar_url(f"{base}/{chave}", final)
        if sha256(final) != info["sha256"]:
            os.remove(final); sys.exit(f"{info['pasta']}/{info['nome']}: SHA-256 não confere; rode de novo")
    print(json.dumps({"raiz": raiz, "ok": True}, ensure_ascii=False))


def conferir(raiz):
    p = os.path.join(raiz, "manifesto.json")
    if not os.path.exists(p):
        print(json.dumps({"ok": False, "motivo": "modelos não baixados", "raiz": raiz}, ensure_ascii=False)); return 1
    man = json.load(open(p))
    faltam = [f"{i['pasta']}/{i['nome']}" for i in man["arquivos"].values()
              if not os.path.exists(os.path.join(raiz, i["pasta"], i["nome"])) or os.path.getsize(os.path.join(raiz, i["pasta"], i["nome"])) != i["tamanho"]]
    print(json.dumps({"ok": not faltam, "faltam": faltam, "raiz": raiz}, ensure_ascii=False))
    return 1 if faltam else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("acao", choices=["baixar", "espelhar", "conferir"])
    ap.add_argument("--repo", default=os.environ.get("LOCUCAO_MODELOS_REPO", "enrico392/agente-marketing-modelos")); ap.add_argument("--tag", default=TAG)
    ap.add_argument("--destino", default=RAIZ); ap.add_argument("--saida", default="modelos")
    a = ap.parse_args()
    if a.acao == "espelhar":
        espelhar(a.saida, os.environ.get("LOCUCAO_ORIGEM_LOCAL"))
    elif a.acao == "baixar":
        baixar(a.repo, a.tag, a.destino)
    else:
        sys.exit(conferir(a.destino))
