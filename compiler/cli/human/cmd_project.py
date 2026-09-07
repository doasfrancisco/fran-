import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

from . import cmd_map, decompiler

WORD = "project"
CROSS_RE = re.compile(r"^(.+?):e(\d+):(.+)$")

SYNC_PROMPT = """The project changed. Explanation texts were written for the old state of the project. Mend the words the change made wrong, and add a sentence for each behaviour the change added.

The project is at <root>. These files of the project changed — read each one before you answer; the diff below shows only the changed lines, not the blocks around them:

<changed>

The unified diff of the change:

<diff>

Pins whose target is gone:

<broken>

The files of the project:

<files>

The candidate entries, each with its full text:

<candidates>

Anchors look like [words](path/of/file), [words](path/of/file:block), [words](path/of/file:e1:anchor words) — an anchor of entry 1 of that file's map — or [words](e1:anchor words) — an anchor of an earlier entry of this map. The rules:
- A text line is stale only when the change makes its words wrong.
- Rewrite a stale line with the smallest edit. Keep every line the change does not touch verbatim. Keep the vocabulary, the layout, and the indentation.
- Keep every anchor. When a block was renamed, keep the anchor words and update the target to the new block name. When a file moved, keep the words and update the path. When an anchor of a file's entry was reworded, keep the words and update the target to the new anchor words.
- These anchor words are pointed at by other entries and must survive unchanged:
<needed>
- When the change adds a behaviour the reader would ask about — a new command, a new step, a new case — add a sentence for it where the reader meets it, in the style of the text. The reader does not read code: say what the thing does, not its class.
- An entry whose words all still hold gets no key in the answer.

Return one JSON object and nothing else:

{"texts": {"<entry id>": "<the full corrected text>"}}
"""


def root_of():
    return decompiler.find_root(Path.cwd())


def map_path(root):
    return root / "human" / "project.json"


def load(root):
    return cmd_map.load_map(map_path(root), WORD)


def save(root, data):
    map_path(root).write_text(json.dumps(data, indent=2) + "\n")


def files_of(root):
    return json.loads((root / "human" / "human.json").read_text()).get("files", [])


def map_of(root, fname):
    mp = decompiler.map_path_of(root / fname, root)
    if not mp.exists():
        return None
    return json.loads(mp.read_text())


def entry_of(data, eid):
    return next((e for e in data["explanations"] if e["id"] == eid), None)


def cross_anchor(words, fname, eid, aw, root):
    fp = root / fname
    assert fp.is_file(), \
        f"[ANCHOR-TARGET] the anchor {words!r} names {fname!r}, which is not a file of the project"
    d = map_of(root, fname)
    assert d, f"[ANCHOR-TARGET] the anchor {words!r} names {fname}, which has no map yet"
    e = entry_of(d, eid)
    assert e, f"[ANCHOR-TARGET] the anchor {words!r} names entry {eid} of {fname}, which does not exist"
    assert aw in {x["words"] for x in e.get("anchors", [])}, \
        f"[ANCHOR-TARGET] entry {eid} of {fname} has no anchor {aw!r}"
    return {"words": words, "file": fname, "entry": eid, "anchor": aw}


def build_anchors(text, data, self_id, root):
    seen = set()
    out = []
    for m in decompiler.ANCHOR_RE.finditer(text):
        words = m.group(1).strip()
        assert words, "[ANCHOR-WORDS] an anchor needs words inside the brackets"
        assert words not in seen, \
            f"[ANCHOR-WORDS] the anchor {words!r} appears twice; anchor words are unique in one text"
        seen.add(words)
        c = CROSS_RE.match(m.group(2).strip())
        if c:
            out.append(cross_anchor(words, c.group(1).strip(), int(c.group(2)), c.group(3).strip(), root))
        else:
            out += decompiler.build_anchors(m.group(0), data, {}, self_id, root)
    return out


def pins_into(root, code_name, eid):
    mp = map_path(root)
    if not mp.exists():
        return set()
    data = json.loads(mp.read_text())
    return {x["anchor"] for e in data["explanations"] for x in e.get("anchors", [])
            if x.get("file") == code_name and x.get("entry") == eid}


def mark_stale(root, code_name, eid, old_text):
    mp = map_path(root)
    if not mp.exists():
        return []
    data = json.loads(mp.read_text())
    ids = []
    for e in data["explanations"]:
        if any(x.get("file") == code_name and x.get("entry") == eid for x in e.get("anchors", [])):
            e["stale"] = {"parent": eid, "file": code_name, "old_text": old_text}
            ids.append(e["id"])
    if ids:
        save(root, data)
    return ids


def counts(anchors):
    files = sum(1 for x in anchors if "file" in x and "entry" not in x)
    cross = sum(1 for x in anchors if "entry" in x)
    same = sum(1 for x in anchors if "explanation" in x)
    return (f"{len(anchors)} anchors ({files} into files, {cross} into entries of other maps, "
            f"{same} into earlier explanations)")


def print_coverage(root, data):
    files = files_of(root)
    pinned = {x["file"] for e in data["explanations"] for x in e.get("anchors", []) if "file" in x}
    left = [f for f in files if f not in pinned]
    print(f"covered: {len(files) - len(left)} of {len(files)} files")
    print("not covered: " + (", ".join(left) if left else "nothing"))


def cmd_map_project(a):
    if a.block:
        sys.exit("the project map has no blocks of its own; drop --block")
    root = root_of()
    data = load(root)
    text = decompiler.read_text_arg(a)
    eid = cmd_map.next_id(data)
    try:
        anchors = build_anchors(text, data, eid, root)
        decompiler.check_cycle(data, eid, anchors)
    except AssertionError as e:
        sys.exit(str(e))
    data["explanations"].append({"id": eid, "block": WORD, "block_lines": [],
                                 "text": text, "anchors": anchors})
    save(root, data)
    print(f"entry {eid}: {WORD}, {counts(anchors)}")
    print_coverage(root, data)
    print(f"wrote {map_path(root)}")


def cmd_retext(a):
    root = root_of()
    data = load(root)
    entry = entry_of(data, a.id)
    if entry is None:
        sys.exit(f"no entry {a.id} in project.json")
    text = decompiler.read_text_arg(a)
    need = decompiler.needed_words(data, a.id)
    try:
        anchors = build_anchors(text, data, a.id, root)
        gone = need - {x["words"] for x in anchors}
        assert not gone, f"[RETEXT-ANCHORS] other entries point at the anchors {sorted(gone)}; " \
                         "the new text must keep them"
        decompiler.check_cycle(data, a.id, anchors)
    except AssertionError as e:
        sys.exit(str(e))
    old_text = entry["text"]
    entry["text"] = text
    entry["anchors"] = anchors
    entry.pop("stale", None)
    kids = decompiler.mark_children(data, a.id, old_text) if text != old_text else []
    save(root, data)
    print(f"entry {a.id} ({WORD}): text replaced, {counts(anchors)}")
    if kids:
        print(f"entries {', '.join(map(str, kids))} depend on entry {a.id} and are marked stale; "
              f"repair each with human sync project --stale <id>")
    print(f"wrote {map_path(root)}")


def cmd_undo(a):
    root = root_of()
    data = load(root)
    if not data["explanations"]:
        sys.exit("nothing to undo")
    last = data["explanations"][-1]
    kids = [e["id"] for e in decompiler.children_of(data, last["id"])]
    if kids:
        sys.exit(f"entries {kids} point at entry {last['id']} through anchors; undo them first")
    data["explanations"].pop()
    save(root, data)
    print(f"removed entry {last['id']}: {WORD}")
    print(f"wrote {map_path(root)}")


def check_cross(x, root):
    d = map_of(root, x["file"])
    if not d:
        return f"{x['file']} has no map"
    e = entry_of(d, x["entry"])
    if not e:
        return f"entry {x['entry']} of {x['file']} does not exist"
    if x["anchor"] not in {y["words"] for y in e.get("anchors", [])}:
        return f"entry {x['entry']} of {x['file']} has no anchor {x['anchor']!r}"
    return None


def cmd_show(a):
    root = root_of()
    if not map_path(root).exists():
        print(f"no map file at {map_path(root)}")
        return
    data = load(root)
    warnings = []
    for e in data["explanations"]:
        tail = ""
        if e.get("stale"):
            st = e["stale"]
            where = f"{st['file']} entry {st['parent']}" if st.get("file") else f"explanation {st['parent']}"
            tail = f"  stale ({where} changed)"
        print(f"{e['id']:3}  {WORD:<24} {'-':<14} {len(e.get('anchors', []))} anchors{tail}")
        derived = [m.group(1).strip() for m in decompiler.ANCHOR_RE.finditer(e["text"])]
        stored = [x["words"] for x in e.get("anchors", [])]
        if derived != stored:
            warnings.append(f"entry {e['id']}: the anchors in the text do not match the stored anchors; "
                            f"rebuild the entry with human retext")
        for x in e.get("anchors", []):
            if "entry" in x:
                bad = check_cross(x, root)
                if not (root / x["file"]).is_file():
                    bad = f"{x['file']} is not in the folder"
                if bad:
                    warnings.append(f"entry {e['id']}: the anchor {x['words']!r}: {bad}; run human sync project")
            elif "file" in x:
                fp = root / x["file"]
                if not fp.is_file():
                    warnings.append(f"entry {e['id']}: the anchor {x['words']!r} names the file "
                                    f"{x['file']!r}, which is not in the folder")
                elif "block" in x:
                    fspans = decompiler.block_spans(fp, fp.read_text().splitlines())
                    if x["block"] not in fspans:
                        warnings.append(f"entry {e['id']}: the anchor {x['words']!r} names the block "
                                        f"{x['block']!r}, which is not in {x['file']}; run human sync project")
                    elif x.get("lines") != [list(fspans[x["block"]])]:
                        warnings.append(f"entry {e['id']}: the anchor {x['words']!r} holds old lines "
                                        f"for {x['file']}:{x['block']}; run human sync project")
            else:
                parent = entry_of(data, x["explanation"])
                if not parent or x["anchor"] not in {y["words"] for y in parent.get("anchors", [])}:
                    warnings.append(f"entry {e['id']}: the anchor {x['words']!r} points at "
                                    f"e{x['explanation']}:{x['anchor']}, which does not exist")
    for w in warnings:
        print(f"warning: {w}")
    print_coverage(root, data)


def cmd_lines(a):
    sys.exit("the project has no lines of its own; ask for a file")


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def old_text_of(root, rel):
    code, out = git(root, "show", f"HEAD:{rel}")
    return out if code == 0 else ""


def changed_files(root, data):
    code, out = git(root, "diff", "HEAD", "--name-only")
    if code != 0:
        sys.exit("the old state of the project is git HEAD; no commit was found")
    changed = set(out.split())
    _, others = git(root, "ls-files", "--others", "--exclude-standard")
    changed |= set(others.split())
    known = set(files_of(root))
    known |= {x["file"] for e in data["explanations"] for x in e.get("anchors", []) if "file" in x}
    return sorted(c for c in changed if c in known)


def project_diff(root, changed):
    out = []
    for rel in changed:
        old = old_text_of(root, rel).splitlines()
        fp = root / rel
        new = fp.read_text().splitlines() if fp.is_file() else []
        out += difflib.unified_diff(old, new, f"a/{rel}", f"b/{rel}", lineterm="")
    return "\n".join(out)


def re_resolve(data, root):
    broken = decompiler.re_resolve(data, WORD, {}, 0, root)
    for e in data["explanations"]:
        for x in e.get("anchors", []):
            if "entry" in x and (root / x["file"]).is_file():
                bad = check_cross(x, root)
                if bad:
                    broken.append((e["id"], f"{x['file']}:e{x['entry']}:{x['anchor']}"))
    return broken


def broken_note(broken, root):
    if not broken:
        return "none"
    lines = []
    for eid, name in broken:
        c = CROSS_RE.match(name)
        tail = ""
        if c:
            d = map_of(root, c.group(1))
            e = entry_of(d, int(c.group(2))) if d else None
            if e:
                words = ", ".join(repr(x["words"]) for x in e.get("anchors", []))
                tail = f"; the anchors of entry {c.group(2)} of {c.group(1)} are now: {words}"
        lines.append(f"entry {eid}: {name}{tail}")
    return "\n".join(lines)


def rebuild(trial, texts, cand, root):
    for e in sorted(trial["explanations"], key=lambda x: x["id"]):
        newt = texts.get(str(e["id"]))
        if newt is not None:
            assert e["id"] in cand, f"[SYNC-TEXTS] entry {e['id']} is not a candidate"
            assert newt.strip(), f"[SYNC-TEXTS] the text of entry {e['id']} is empty"
            e["text"] = newt.strip()
        try:
            anchors = build_anchors(e["text"], trial, e["id"], root)
        except AssertionError as err:
            raise AssertionError(f"in the text of entry {e['id']}: {err}") from None
        need = decompiler.needed_words(trial, e["id"])
        gone = need - {x["words"] for x in anchors}
        assert not gone, f"[SYNC-ANCHORS] other entries point at the anchors {sorted(gone)} of " \
                         f"entry {e['id']}; the new text must keep them"
        e["anchors"] = anchors
    for e in trial["explanations"]:
        for x in e.get("anchors", []):
            if "explanation" not in x:
                continue
            parent = entry_of(trial, x["explanation"])
            assert x["anchor"] in {y["words"] for y in parent["anchors"]}, \
                f"[SYNC-ANCHORS] entry {e['id']} points at e{x['explanation']}:{x['anchor']}, " \
                f"which the new text of entry {x['explanation']} dropped"


def ask(prompt, root, tries, check):
    last = ""
    suffix = ""
    for _ in range(tries):
        try:
            m = decompiler.ask_claude(prompt + suffix, root)
        except (ValueError, KeyError) as e:
            last = f"the answer was not one JSON object: {e}"
            suffix = "\n\nYour previous answer was not one JSON object. Return only the JSON."
            continue
        try:
            return check(m)
        except AssertionError as e:
            last = str(e)
            suffix = f"\n\nYour previous answer:\n{json.dumps(m)}\n\n" \
                     f"It broke this rule: {last}\nReturn the full corrected JSON object."
    sys.exit(f"the repair failed after {tries} tries, last error: {last}")


def repair_stale(a, root, data):
    entry = entry_of(data, a.stale)
    if entry is None:
        sys.exit(f"no entry {a.stale} in project.json")
    st = entry.get("stale")
    if not st:
        sys.exit(f"entry {a.stale} is not stale")
    if st.get("file"):
        d = map_of(root, st["file"])
        parent = entry_of(d, st["parent"]) if d else None
        home = f"Explanation {st['parent']} lives in the map of {st['file']}; a pin at one of its " \
               f"anchors reads [words]({st['file']}:e{st['parent']}:anchor words).\n\n"
    else:
        parent = entry_of(data, st["parent"])
        home = ""
    if parent is None:
        sys.exit(f"explanation {st['parent']} no longer exists; retext entry {a.stale} instead")
    need = decompiler.needed_words(data, entry["id"])
    parent_diff = "\n".join(difflib.unified_diff(st["old_text"].splitlines(), parent["text"].splitlines(),
                                                 "old", "new", lineterm=""))
    prompt = decompiler.STALE_PROMPT
    if st.get("file"):
        prompt = prompt.replace("e<pid>:", f"{st['file']}:e<pid>:")
    prompt = (home + prompt.replace("<pid>", str(parent["id"]))
              .replace("<old_parent>", st["old_text"])
              .replace("<new_parent>", parent["text"])
              .replace("<parent_diff>", parent_diff)
              .replace("<child>", entry["text"])
              .replace("<needed>", ", ".join(sorted(need)) or "none"))

    def check(m):
        t = (m.get("text") or "").strip()
        assert t, "[STALE-TEXT] the answer needs the full dependent text"
        anchors = build_anchors(t, data, entry["id"], root)
        gone = need - {x["words"] for x in anchors}
        assert not gone, f"[STALE-ANCHORS] other entries point at the anchors {sorted(gone)}; " \
                         "the text must keep them"
        decompiler.check_cycle(data, entry["id"], anchors)
        return t, anchors

    text, anchors = ask(prompt, root, a.tries, check)
    old_text = entry["text"]
    entry["text"] = text
    entry["anchors"] = anchors
    entry.pop("stale")
    decompiler.report_text_diff(entry["id"], old_text, text)
    if text == old_text:
        print(f"entry {entry['id']}: no word changed")
    kids = decompiler.mark_children(data, entry["id"], old_text) if text != old_text else []
    if kids:
        print(f"entries {', '.join(map(str, kids))} depend on entry {entry['id']} and are marked stale")
    save(root, data)
    print_coverage(root, data)
    print(f"wrote {map_path(root)}")


def cmd_sync(a):
    if a.old:
        sys.exit("the old state of the project is git HEAD; --old has no meaning here")
    root = root_of()
    if not map_path(root).exists():
        sys.exit(f"no map file at {map_path(root)}")
    data = load(root)
    if a.stale is not None:
        repair_stale(a, root, data)
        return
    changed = changed_files(root, data)
    broken = re_resolve(data, root)
    broken_ids = {eid for eid, name in broken}
    cand = {e["id"] for e in data["explanations"]
            if any(x.get("file") in changed for x in e.get("anchors", []))} | broken_ids
    print(f"changed files: {', '.join(changed) if changed else 'none'}")
    for eid, name in broken:
        print(f"entry {eid}: {name!r} is gone")
    if not cand:
        save(root, data)
        print("no entry touches the change, every pin re-resolved, no claude call")
        print(f"wrote {map_path(root)}")
        return
    print(f"candidate entries: {', '.join(str(i) for i in sorted(cand))}")
    changed_note = "\n".join(
        f"{rel} — {root / rel}" + ("" if (root / rel).is_file() else " (gone)") for rel in changed) or "none"
    cands = "\n\n".join(f"=== entry {e['id']} ===\n{e['text']}"
                        for e in data["explanations"] if e["id"] in cand)
    needed = "\n".join(f"entry {i}: {', '.join(sorted(decompiler.needed_words(data, i)))}"
                       for i in sorted(cand) if decompiler.needed_words(data, i)) or "none"
    prompt = (SYNC_PROMPT.replace("<root>", str(root))
              .replace("<changed>", changed_note)
              .replace("<diff>", project_diff(root, changed) or "none")
              .replace("<broken>", broken_note(broken, root))
              .replace("<files>", "\n".join(files_of(root)))
              .replace("<candidates>", cands)
              .replace("<needed>", needed))

    def check(m):
        texts = m.get("texts") or {}
        assert isinstance(texts, dict), "[SYNC-SHAPE] texts is an object keyed by entry id"
        t = json.loads(json.dumps(data))
        rebuild(t, texts, cand, root)
        return t

    trial = ask(prompt, root, a.tries, check)
    stale_kids = set()
    for e in trial["explanations"]:
        before = entry_of(data, e["id"])
        if e["text"] != before["text"]:
            decompiler.report_text_diff(e["id"], before["text"], e["text"])
            stale_kids.update(decompiler.mark_children(trial, e["id"], before["text"]))
    if stale_kids:
        print(f"entries {', '.join(map(str, sorted(stale_kids)))} depend on a changed entry and are "
              f"marked stale; repair each with human sync project --stale <id>")
    save(root, trial)
    print_coverage(root, trial)
    print(f"wrote {map_path(root)}")


def snapshot(root, kind):
    data = load(root)
    if kind == "sync":
        changed = changed_files(root, data)
        files = {rel: (root / rel).read_text() for rel in changed if (root / rel).is_file()}
        return {"changed": changed, "files": files, "diff": project_diff(root, changed)}
    return {"files": {rel: (root / rel).read_text() for rel in files_of(root) if (root / rel).is_file()}}


COMMANDS = {"retext": cmd_retext, "undo": cmd_undo, "show": cmd_show,
            "lines": cmd_lines, "sync": cmd_sync}
