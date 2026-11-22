#!/usr/bin/env python3
import argparse, csv, hashlib, html, json, re, sqlite3, tempfile, time, unicodedata, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template" / "sample.apkg"
DECKS_DIR = ROOT / "decks"
OUTPUT_DIR = ROOT / "output"
COLUMN_TO_FIELD = {
    "Vocabulary": "Hanzi",
    "Pronunciation": "Pinyin",
    "English": "English",
    "Vietnamese": "Vietnamese",
    "Example": "Example",
    "Sentence Pinyin": "Sentence Pinyin",
    "Sentence Translation": "Sentence Translation",
}
BASE91 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~"


def guid_for(*parts):
    n = int.from_bytes(hashlib.sha256("\x1f".join(parts).encode()).digest()[:8], "big")
    out = ""
    while n:
        n, r = divmod(n, len(BASE91))
        out = BASE91[r] + out
    return out


def strip_html(s):
    s = re.sub(r"(?is)<style.*?</style>|<script.*?</script>", "", s)
    return html.unescape(re.sub(r"(?s)<.*?>", "", s))


def csum(s):
    return int(hashlib.sha1(strip_html(s).encode()).hexdigest()[:8], 16)


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def tsv_order(path):
    m = re.match(r"\d+", path.name)
    return (int(m.group()) if m else float("inf"), path.name)


def read_tsv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [[c.strip() for c in r] for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if any(c.strip() for c in r)]
    header, data = rows[0], rows[1:]
    if header != list(COLUMN_TO_FIELD):
        raise SystemExit(f"{path.name}: unexpected header {header}, expected {list(COLUMN_TO_FIELD)}")
    for n, r in enumerate(data, 2):
        if len(r) != len(header) or not r[0]:
            raise SystemExit(f"{path.name}: bad row #{n}: {r}")
    return [dict(zip(header, r)) for r in data]


def main():
    parser = argparse.ArgumentParser(description="Build output/NAME.apkg from decks/NAME/*.tsv (note type taken from template/sample.apkg, audio fields left empty).")
    parser.add_argument("name", help="folder under decks/; also the parent deck name unless --deck is given")
    parser.add_argument("--deck", help='parent deck name in Anki, e.g. "B. 读书::越南美食" (default: NAME)')
    args = parser.parse_args()

    tsv_dir = DECKS_DIR / args.name
    files = sorted(tsv_dir.glob("*.tsv"), key=tsv_order)
    if not files:
        available = sorted(p.name for p in DECKS_DIR.iterdir() if p.is_dir()) if DECKS_DIR.is_dir() else []
        raise SystemExit(f"no .tsv files in {tsv_dir} (available: {available})")
    deck_path = [p.strip() for p in unicodedata.normalize("NFC", args.deck or args.name).split("::")]
    if not all(deck_path):
        raise SystemExit(f"invalid deck name {args.deck or args.name!r}")
    parent = "::".join(deck_path)
    out = OUTPUT_DIR / f"{args.name}.apkg"
    rebuilt = out.exists()

    now_ms = int(time.time() * 1000)
    now = now_ms // 1000
    with zipfile.ZipFile(TEMPLATE) as z:
        try:
            meta, stub, template_db = z.read("meta"), z.read("collection.anki2"), z.read("collection.anki21")
        except KeyError as e:
            raise SystemExit(f'{TEMPLATE}: {e.args[0]}; re-export it from Anki with "Support older Anki versions" ticked')

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "collection.anki21"
        db_path.write_bytes(template_db)
        db = sqlite3.connect(db_path, isolation_level=None)
        conf_json, models_json, decks_json = db.execute("select conf, models, decks from col").fetchone()
        (model,) = json.loads(models_json).values()
        field_names = [f["name"] for f in sorted(model["flds"], key=lambda f: f["ord"])]
        missing = set(COLUMN_TO_FIELD.values()) - set(field_names)
        if missing:
            raise SystemExit(f"note type {model['name']} lacks fields {missing}")
        old_decks = json.loads(decks_json)
        (template_did,) = db.execute("select distinct did from cards").fetchone()
        template = old_decks[str(template_did)]

        ids = iter(range(now_ms, now_ms + 10**6))
        decks = {"1": old_decks["1"]}

        def add_deck(name):
            did = next(ids)
            decks[str(did)] = {**template, "id": did, "name": name, "mod": now, "usn": -1, "collapsed": False, "desc": "",
                               **{k: [0, 0] for k in ("lrnToday", "revToday", "newToday", "timeToday")}}
            return did

        db.execute("begin")
        for table in ("notes", "cards", "revlog", "graves"):
            db.execute(f"delete from {table}")
        for depth in range(1, len(deck_path) + 1):
            add_deck("::".join(deck_path[:depth]))
        pos, summary, seen = 0, [], {}
        for path in files:
            name = unicodedata.normalize("NFC", path.stem)
            did = add_deck(f"{parent}::{name}")
            rows = read_tsv(path)
            summary.append((name, len(rows)))
            for row in rows:
                vocab = row["Vocabulary"]
                if vocab in seen:
                    raise SystemExit(f"{path.name}: duplicate Vocabulary {vocab!r} (already in {seen[vocab]})")
                seen[vocab] = path.name
                pos += 1
                nid = next(ids)
                values = {COLUMN_TO_FIELD[c]: html.escape(v, quote=False) for c, v in row.items()}
                fields = [values.get(n, "") for n in field_names]
                db.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
                           (nid, guid_for(str(model["id"]), vocab), model["id"], now, -1, "",
                            "\x1f".join(fields), strip_html(fields[model["sortf"]]), csum(fields[0]), 0, ""))
                db.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (nid, nid, did, 0, now, -1, 0, 0, pos, 0, 0, 0, 0, 0, 0, 0, 0, "{}"))
        conf = json.loads(conf_json)
        conf.update(curModel=model["id"], nextPos=pos + 1)
        db.execute("update col set mod=?, scm=?, conf=?, decks=?", (now_ms, now_ms, dumps(conf), dumps(decks)))
        db.execute("commit")
        db.execute("vacuum")
        db.close()

        OUTPUT_DIR.mkdir(exist_ok=True)
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("meta", meta, compress_type=zipfile.ZIP_STORED)
            z.write(db_path, "collection.anki21", compress_type=zipfile.ZIP_DEFLATED)
            z.writestr("collection.anki2", stub, compress_type=zipfile.ZIP_STORED)
            z.writestr("media", "{}", compress_type=zipfile.ZIP_STORED)

    for name, n in summary:
        print(f"{parent}::{name}: {n}")
    print(f"total {pos} notes -> {out} ({out.stat().st_size} bytes)")
    if rebuilt:
        print('note: this replaced an earlier build. If that build is already in Anki, import this file with "Update notes: Never" '
              '(adds only the new words); the default "If newer" overwrites every note and clears Audio/SP.')


if __name__ == "__main__":
    main()
