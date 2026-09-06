# desk

The detailed telling of a file that only dispatches: it reads what the user types and hands it to the part that does the work. One head per thing the user can type, the part that does it pinned on the right, and the shared machinery told once, where it stands.

Validated on: compiler/cli/human/__init__.py — training session 20260905-205439-5e90.

## Rules

- One to three lines at the top say what the file is: the front desk. It does not do the work itself; it reads what you typed and passes it on.
- One head per command the user types, written as the user types it — `human init`, `human serve` — with the block that does it pinned on the right: `([the register](cmd_init))`.
- Under each head stand two to six full sentences, indented: what the command makes, where it lands, and why. The parts the command uses get their pins inline in the sentences, not in the head.
- When a part answers several kinds of asks — a door that answers calls from a browser — list the asks as short aligned lines under the sentences, one per kind, what each one gives back on the right.
- A command whose work lives in another file gets a file pin on the right and one or two sentences. The desk only points the way.
- The last lines name the block that ties the commands together — the front door — and say what it does with the typed line.
- No programming words. Say what the thing does in place of its class.

## Example

```
This file is the front desk of the notes tool. It does not keep
the notes itself: it reads what you typed and passes it to the
hand that does it. Here is what each thing you can type becomes.

notes add "call the bank"                       ([the writer](cmd_add))
    Puts one note into the book with the moment it came.
    The book is one file in the folder, made on the first note.

notes list                                       ([the reader](cmd_list))
    Prints every note, newest first, so the last one you wrote
    is the first you see.

notes serve                                        ([the shelf](cmd_serve))
    Opens a door for the browser on port 8000 and answers
    two kinds of knocks:
      /                     — the page that shows the book
      /notes.json           — the book itself, read fresh on every ask

notes sync                                   ([the engine](notes/sync.py))
    Brings the book up to date with the other machine.
    The desk only points the way.

The one line that ties it together is [the front door](main):
it names every command above, says which flags each one takes,
and hands the typed line to the right hand.
```
