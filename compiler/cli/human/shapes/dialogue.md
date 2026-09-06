# dialogue

The telling of a rulebook — a skill, a procedure a person and a tool run together — as the exchange itself: who says what, in the order it happens, and what the tool does between the turns. Each turn pins the section of the document that rules it.

Validated on: compiler/cli/human/skills/decompile/SKILL.md — training sessions 20260905-201816-0276 and 20260905-205439-5e90.

## Rules

- One or two lines at the top say what the document is and how many loops run through it.
- One block per loop, with a name line: "The everyday loop — one file, one abstraction:".
- Inside a loop every turn starts with who speaks. The user's turn is `you:` and the words said, in quotes, or the command typed. What claude or the tool does stands indented under it, one act per line.
- The pin of a turn sits on the right, at the section of the document that rules it: `([map](3. Map))`. For a markdown file the pin is the heading's real text.
- A choice inside a turn — three versions, two roads — is a short aligned list under the turn, one line per case.
- After the loops, one short paragraph for what the loops share — the step both meet — and one line that says the whole document in one sentence, pinned at the top heading.
- Keep claude and the tool apart: claude writes and shows, the tool checks and writes the files. Every turn says which one acts.
- No programming words. Say what the thing does in place of its class.

## Example

```
The skill is the rulebook claude reads before it reviews a change
for you. One loop runs through it.

The review loop — one change, one verdict:

    you: "review my last commit"
         claude reads the change and lists what it sees
         wrong, one line per finding                  ([findings](2. Findings))
         each line names the file and the line
         claude shows the list and stops.
    you: "fix 1 and 3"
         claude edits those two, and only those            ([fixes](3. Fixes))
         the tool runs the tests
         claude says what passed and what did not          ([report](4. Report))

What the skill is, in one line: claude finds and fixes on your
word, the tool proves it                                   ([review](review))
```
