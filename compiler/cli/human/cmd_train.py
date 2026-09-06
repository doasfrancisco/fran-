import argparse
import json
import os
import secrets
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from . import cmd_map, decompiler

SLOTS = ("best", "refinement", "free")
LOCK = threading.Lock()


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def as_version(v):
    if v is None or isinstance(v, dict):
        return v
    return {"text": v, "shape": None, "at": None, "history": []}


def version_text(v):
    v = as_version(v)
    return v["text"] if v else None


def version(text, shape, old=None):
    old = as_version(old)
    history = old["history"] + [{k: old[k] for k in ("text", "shape", "at")}] if old else []
    return {"text": text, "shape": shape, "at": now(), "history": history}


def training_dir(root):
    return root / "human" / "training"


def session_paths(root):
    d = training_dir(root)
    if not d.is_dir():
        return []
    return sorted(d.glob("*.json"), key=lambda p: p.stem, reverse=True)


def load_session(path):
    return json.loads(path.read_text())


def save_session(path, data):
    data["edited"] = now()
    path.write_text(json.dumps(data, indent=2) + "\n")


def open_session(root):
    d = training_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    for p in session_paths(root):
        data = load_session(p)
        if not data["finished"]:
            return p, data
    return None, None


def summary(path, data):
    rows = data["rows"]
    return {"session_id": data["session_id"], "created": data["created"],
            "edited": data["edited"], "finished": data["finished"],
            "rows": len(rows), "picked": sum(1 for r in rows if r["picked"]),
            "applied": sum(1 for r in rows if r["applied"])}


def list_sessions(root):
    return [summary(p, load_session(p)) for p in session_paths(root)]


def carry_row(root, old, old_sid):
    code_path = root / old["file"]
    if not code_path.is_file():
        print(f"{old['file']} is gone; its row stays in {old_sid}")
        return None
    a = argparse.Namespace(kind=old["kind"],
                           entry=old["entry"] if old["level"] == "same" else None,
                           block=old["block"] if old["level"] == "above" else None)
    src = code_path.read_text()
    spans = decompiler.block_spans(code_path, src.splitlines())
    data = cmd_map.load_map(decompiler.map_path_of(code_path, root), old["file"])
    try:
        row = new_row(a, root, code_path, old["file"], data, src)
    except SystemExit as e:
        print(f"{old['file']}: {e}; its row stays in {old_sid}")
        return None
    row["carried_from"] = old_sid
    kept, dropped = [], []
    for s in SLOTS:
        v = as_version(old["versions"][s])
        if v is None or (s == "refinement" and row["kind"] == "sync" and v["text"] == old["before"]):
            continue
        try:
            check_text(v["text"], row, data, spans, root)
        except AssertionError:
            dropped.append(s)
            continue
        row["versions"][s] = v
        kept.append(s)
    note = "the code changed; " if src != old["code"] else ""
    print(f"carried {old['file']} from {old_sid}: {note}kept {', '.join(kept) or 'nothing'}"
          + (f", dropped {', '.join(dropped)} — write them again" if dropped else ""))
    return row


def carry(root):
    paths = session_paths(root)
    if not paths:
        return []
    old = load_session(paths[0])
    rows = [carry_row(root, r, old["session_id"]) for r in old["rows"]
            if not r["picked"] and not r["applied"]]
    return [r for r in rows if r]


def cmd_open(root):
    p, data = open_session(root)
    if p:
        sys.exit(f"session {data['session_id']} is still open; close it first with human train --close")
    rows = carry(root)
    sid = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    path = training_dir(root) / f"{sid}.json"
    stamp = now()
    save_session(path, {"session_id": sid, "created": stamp, "edited": stamp,
                        "finished": None, "rows": rows})
    print(f"session {sid} open" + (f" with {len(rows)} carried rows" if rows else ""))
    print(f"wrote {path}")


def pick(root, sid, row, slot, comment=None):
    path = training_dir(root) / f"{sid}.json"
    if not path.is_file():
        return 404, f"no session {sid}"
    if slot is not None and slot not in SLOTS:
        return 400, f"picked must be one of {', '.join(SLOTS)} or null"
    if comment is not None and not isinstance(comment, str):
        return 400, "comment must be text or null"
    with LOCK:
        data = load_session(path)
        if data["finished"]:
            return 409, f"session {sid} is finished"
        if not isinstance(row, int) or not 0 <= row < len(data["rows"]):
            return 400, f"no row {row} in session {sid}"
        r = data["rows"][row]
        if slot is not None and r["versions"][slot] is None:
            return 400, f"row {row} has no {slot} version yet"
        r["picked"] = slot
        r["comment"] = (comment.strip() or None) if slot and comment else None
        r["edited"] = now()
        save_session(path, data)
    return 200, r


def whole_file_entry(data, code_name):
    ids = [e["id"] for e in data["explanations"] if e["block"] == code_name]
    return min(ids) if ids else None


def new_row(a, root, code_path, code_name, data, src):
    entry = None
    if a.kind == "sync":
        if a.block:
            sys.exit("a sync row works on an entry that exists; use --entry, not --block")
        eid = a.entry if a.entry is not None else whole_file_entry(data, code_name)
        entry = next((e for e in data["explanations"] if e["id"] == eid), None)
        if entry is None:
            sys.exit(f"no entry to sync in {decompiler.map_path_of(code_path, root).name}")
        level = "same"
    elif a.entry is not None:
        if a.block:
            sys.exit("give --entry or --block, not both")
        entry = next((e for e in data["explanations"] if e["id"] == a.entry), None)
        if entry is None:
            sys.exit(f"no entry {a.entry} in {decompiler.map_path_of(code_path, root).name}")
        level = "same"
    elif a.block:
        level = "above"
    else:
        level = "first" if not data["explanations"] else "below"
    stamp = now()
    row = {"file": code_name, "kind": a.kind,
           "map": decompiler.map_path_of(code_path, root).relative_to(root).as_posix(),
           "entry": entry["id"] if entry else None, "level": level,
           "block": entry["block"] if entry else a.block,
           "before": entry["text"] if entry else None,
           "code": src,
           "versions": {s: None for s in SLOTS}, "picked": None, "comment": None, "applied": None,
           "created": stamp, "edited": stamp}
    if a.kind == "sync":
        row["versions"]["refinement"] = version(entry["text"], None)
    return row


def check_text(text, row, data, spans, root):
    self_id = row["entry"] if row["level"] == "same" else cmd_map.next_id(data)
    anchors = decompiler.build_anchors(text, data, spans, self_id, root)
    if row["level"] == "same":
        gone = decompiler.needed_words(data, row["entry"]) - {x["words"] for x in anchors}
        assert not gone, f"[RETEXT-ANCHORS] other entries point at the anchors {sorted(gone)}; " \
                         "the text must keep them"
    decompiler.check_cycle(data, self_id, anchors)
    return anchors


def cmd_add(a, root):
    if not a.slot:
        sys.exit("say which version this is: --as best, --as refinement or --as free")
    path, session = open_session(root)
    if not path:
        sys.exit("no open session; start one with human train --open")
    code_path = Path(a.code_file).resolve()
    if not code_path.is_file():
        sys.exit(f"{a.code_file} is not a file")
    code_name = decompiler.rel_name(code_path, root)
    src = code_path.read_text()
    lines = src.splitlines()
    spans = decompiler.block_spans(code_path, lines)
    data = cmd_map.load_map(decompiler.map_path_of(code_path, root), code_name)
    text = decompiler.read_text_arg(a)
    row = next((r for r in session["rows"] if r["file"] == code_name and r["applied"] is None), None)
    made = row is None
    if made:
        row = new_row(a, root, code_path, code_name, data, src)
    elif row["code"] != src:
        sys.exit(f"{code_name} changed since its row was made; close the session and open a new one")
    try:
        anchors = check_text(text, row, data, spans, root)
    except AssertionError as e:
        sys.exit(str(e))
    old = row["versions"][a.slot]
    row["versions"][a.slot] = version(text, a.shape, old)
    row["edited"] = now()
    if made:
        session["rows"].append(row)
    save_session(path, session)
    idx = session["rows"].index(row)
    word = "new row" if made else "row"
    print(f"{word} {idx}: {code_name}, {row['kind']}, {row['level']}"
          + (f" (entry {row['entry']})" if row["entry"] is not None else "")
          + f", {a.slot}" + (f" as {a.shape}" if a.shape else "")
          + f": {decompiler.anchor_counts(anchors)}")
    if old is not None:
        n = len(row["versions"][a.slot]["history"])
        print(f"{a.slot} rewritten; {n} earlier text{'s' if n > 1 else ''} kept in its history")
    filled = [s for s in SLOTS if row["versions"][s] is not None]
    print(f"versions: {', '.join(filled)}")
    print(f"wrote {path}")


def run_with_text(fn, text, **kw):
    fd, tmp = tempfile.mkstemp(suffix=".txt")
    try:
        os.write(fd, text.encode())
        os.close(fd)
        fn(argparse.Namespace(text=tmp, verbatim=None, **kw))
    finally:
        os.unlink(tmp)


def apply_row(root, row):
    code_path = root / row["file"]
    text = version_text(row["versions"][row["picked"]])
    if row["level"] == "same":
        run_with_text(decompiler.cmd_retext, text, code_file=str(code_path), id=row["entry"])
        return row["entry"]
    data = cmd_map.load_map(decompiler.map_path_of(code_path, root), row["file"])
    eid = cmd_map.next_id(data)
    run_with_text(cmd_map.cmd_map, text, code_file=str(code_path), block=row["block"])
    return eid


def cmd_close(root):
    path, session = open_session(root)
    if not path:
        sys.exit("no open session")
    order = sorted(range(len(session["rows"])),
                   key=lambda i: (session["rows"][i]["level"] == "below", i))
    failed = []
    for i in order:
        row = session["rows"][i]
        if not row["picked"] or row["applied"]:
            continue
        print(f"row {i}: {row['file']}, {row['picked']} picked")
        if (root / row["file"]).read_text() != row["code"]:
            row["code_changed"] = True
            print(f"row {i}: the file changed since the row was made; the versions describe the old code")
        try:
            eid = apply_row(root, row)
        except SystemExit as e:
            failed.append(i)
            print(f"row {i} failed: {e}")
            continue
        row["applied"] = {"entry": eid, "at": now()}
        row["edited"] = now()
        save_session(path, session)
    rows = session["rows"]
    picked = sum(1 for r in rows if r["picked"])
    if failed:
        save_session(path, session)
        sys.exit(f"{len(failed)} of {picked} picked rows failed ({', '.join(map(str, failed))}); "
                 f"the session stays open — correct and close again")
    session["finished"] = now()
    save_session(path, session)
    left = len(rows) - picked
    print(f"session {session['session_id']} finished: {len(rows)} rows, {picked} picked and applied, "
          f"{left} without a pick" + ("; they carry over to the next session" if left else ""))
    print(f"wrote {path}")


def cmd_train(a):
    if a.open or a.close:
        if a.code_file:
            sys.exit("--open and --close take no file")
        root = decompiler.find_root(Path.cwd())
        (cmd_open if a.open else cmd_close)(root)
        return
    if not a.code_file:
        sys.exit("give a file, or --open / --close")
    root = decompiler.find_root(Path(a.code_file).resolve())
    cmd_add(a, root)
