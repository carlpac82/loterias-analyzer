#!/usr/bin/env python3
"""Recolhe da página de resultados dos Jogos Santa Casa os valores dos prémios
do Euromilhões e do EuroDreams e o código vencedor do M1lhão.

Os dados são gravados em ficheiros JSONL na raiz do repositório, deduplicados
por data + número de sorteio. Se a página ainda não tiver o sorteio novo,
simplesmente não acrescenta nada (idempotente).
"""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; LoteriasAnalyzer/2.1)"}

PAGES = {
    "euro": "https://www.jogossantacasa.pt/web/ResultsBoard/euromilhoes",
    "dream": "https://www.jogossantacasa.pt/web/ResultsBoard/EuroDreams",
    "m1lhao": "https://www.jogossantacasa.pt/web/ResultsBoard/m1lhao",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("iso-8859-1")


def parse_eur(text: str):
    """'&euro; 64.399,89' / '&#8364; 450,22' / '&#8364; 20.000&#47;mês x 30 anos' -> valor."""
    t = re.sub(r"<[^>]+>", "", text).strip()
    t = t.replace("&#8364;", "€").replace("&euro;", "€").replace("&#47;", "/").replace("&nbsp;", " ").strip()
    m = re.search(r"€\s*([\d.]+),(\d{2})", t)          # valor único em euros
    if m:
        return float(m.group(1).replace(".", "") + "." + m.group(2))
    m = re.search(r"€\s*([\d.]+)\s*/mês\s*x\s*(\d+)\s*anos", t)  # anuidade
    if m:
        return f"{m.group(1)} €/mês × {m.group(2)} anos"
    return None


def parse_draw(html: str, game: str):
    draw = re.search(r"Sorteio:\s*(\S+)", html)
    date = re.search(r"Data do Sorteio\s*-\s*(\d{2})/(\d{2})/(\d{4})", html)
    if not draw or not date:
        raise RuntimeError(f"{game}: sorteio/data não encontrados")
    iso = f"{date.group(3)}-{date.group(2)}-{date.group(1)}"

    if game == "m1lhao":
        code = re.search(r'id="code_m1"[^>]*>\s*([A-Z]{2,4}\s*\d{4,6})\s*<', html)
        if not code:
            raise RuntimeError("m1lhao: código não encontrado")
        return {
            "draw": draw.group(1),
            "date": iso,
            "code": re.sub(r"\s+", "", code.group(1)),
        }

    prizes, ptw, tw = {}, [], []
    rows = re.findall(
        r'<ul class="colums">\s*<li>\s*(\d+)\.\s*º?\s*Prémio\s*</li>\s*<li>([\s\S]*?)</li>'
        r'\s*<li class="litleCol">\s*([\d\s.,]+?)\s*</li>\s*<li class="litleCol">\s*([\d\s.,]+?)\s*</li>'
        r"\s*<li>([\s\S]*?)</li>\s*</ul>",
        html,
    )
    if not rows:
        raise RuntimeError(f"{game}: tabela de prémios não encontrada")
    for tier, _desc, wpt, wtot, val in rows:
        t = int(tier)
        prizes[t] = parse_eur(val)
        ptw.append(int(re.sub(r"[\s.]", "", wpt) or 0))
        tw.append(int(re.sub(r"[\s.]", "", wtot) or 0))

    rec = {"draw": draw.group(1), "date": iso, "prizes": prizes,
           "winners_pt": ptw, "winners_total": tw}
    if game == "euro":
        m = re.search(r"Previs[aã]o 1º Prémio[^<]*</li>\s*<li[^>]*>\s*&euro;\s*([\d.,]+)", html)
        if m:
            rec["jackpot"] = float(m.group(1).replace(".", "").replace(",", "."))
    return rec


def append_jsonl(path: Path, rec: dict, keys=("date", "draw")) -> bool:
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    seen.add(tuple(str(r.get(k)) for k in keys))
                except json.JSONDecodeError:
                    continue
    key = tuple(str(rec.get(k)) for k in keys)
    if key in seen:
        return False
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return True


def main() -> None:
    out_files = {
        "euro": ROOT / "prizes-euromilhoes.jsonl",
        "dream": ROOT / "prizes-eurodreams.jsonl",
        "m1lhao": ROOT / "m1lhao.jsonl",
    }
    for game, url in PAGES.items():
        try:
            rec = parse_draw(fetch(url), game)
        except Exception as e:
            print(f"[aviso] {game}: {e}")
            continue
        added = append_jsonl(out_files[game], rec)
        print(f"{game}: {rec['date']} ({rec['draw']}) "
              + ("adicionado" if added else "já existia"))


if __name__ == "__main__":
    main()
