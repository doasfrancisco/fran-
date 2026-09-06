# sections

The detailed telling of a code file that is a set of functions. It divides the file on its code sections and keeps the look of an explanation, like the flow of a function: one head per block in story order, the inputs in the head, full sentences under it. The small helpers stand below a rule as one-liners.

Validated on: compiler/cli/human/cmd_train.py — training sessions 20260905-201816-0276 and 20260905-205439-5e90.

## Rules

- One head per block, in story order — the order a reader meets them, not the order of the file.
- The head is the block's name pinned to its block, with the inputs in the order of the code: `[carry_row](carry_row)(root, old, old_sid)`.
- The first sentence under a head says what each input is, in plain words: "old is one row of the last session; old_sid is that session's id." An input that comes from outside — what you typed, a file — gets one real example. An input that is the same in every function is defined once, at its first head, and never again.
- Under each head stand two to six full sentences, indented. Every sentence has a subject — you, the tool, or claude — and a full stop.
- A definition lives in place: the sentence that defines a thing — a row, a session, a level — stands under the head where the reader first meets it, never in a list of words apart from the text.
- A block that exists to feed one step says that purpose: "It exists only so a picked text reaches the old commands the way a typed text would."
- The top of the file — the imports and the names bound at the top — takes one line each before the first head, in plain words: "import the clock, json, the scratch files, and a lock".
- A rule line sets apart the small hands: the helpers of a few lines. Below it, each one is a single line — the pinned name, its inputs, and what it gives back — aligned so they read as a list.
- No programming words. Say what the thing does in place of its class.

## Example

```
import json and the clock

BOOK = notes.json — the one file every note lives in

[cmd_add](cmd_add)(root, text)
    root is the folder of the project; text is the note you typed,
    like `notes add "call the bank"`.
    The tool opens the book, adds the note with the moment it came,
    and writes the book back. A note is one line of text and its
    moment; the book is every note in one file.

[cmd_list](cmd_list)(root)
    The tool prints every note in the book, newest first,
    so the one you wrote last is the one you see first.

[main](main)()
    The door. It reads what you typed — add or list — and hands
    it to the one above that does it.

──────────────────────────────────────
the small hands

[now](now)()                  the moment as text
[book_path](book_path)(root)  the notes file under the root
[load](load)(path)            the book read as data; an empty book when there is none
[save](save)(path, data)      writes the book
```
