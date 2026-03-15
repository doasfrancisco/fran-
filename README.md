# fran++

TLA+ → Python compiler. Write your algorithm as a state machine, compile it to a Python class.

## Usage

```bash
python fran.py spec.tla                # compile to spec.py
python fran.py spec.tla -o out.py      # compile to out.py
python fran.py spec.tla --run          # compile and run
python fran.py spec.tla --ast          # show parsed AST
```

## What it compiles

| TLA+ | Python |
|------|--------|
| `MODULE Name` | `class Name` |
| `VARIABLE x` | `self.x` in `__init__` |
| `Init == x = 0` | `__init__` assignments |
| `Action == guard /\ x' = val` | method with `if guard:` + state update |
| `Next == A \/ B \/ C` | `step()` with `random.choice()` |
| `TypeInvariant == ...` | `check()` with asserts |

## What you can't express yet

TLA+ models pure state transitions. The compiler outputs the state machine skeleton — no real-world side effects. You add those manually on top.

| Can't express | Why | Workaround |
|---------------|-----|------------|
| I/O (`print`, file read/write) | TLA+ has no I/O concept | Add `print()` calls in generated methods |
| Network (HTTP, sockets, APIs) | TLA+ models state, not communication channels | Wrap generated class with request handlers |
| Database operations | Same — no side effects in TLA+ | Call DB inside action methods after state update |
| User input | TLA+ doesn't model external input sources | Feed input as method arguments |
| Time / delays / `sleep` | TLA+ is untimed (steps are abstract) | Add timing logic in Python wrapper |
| Exceptions / error handling | TLA+ uses guards, not try/catch | Add try/except around generated code |
| Async / `await` | Generated code is synchronous | Wrap in async functions |
| Logging / observability | Not a TLA+ concept | Add logging after state transitions |
| String operations | TLA+ has no string manipulation | Use Python strings in wrapper code |
| Floating point math | TLA+ works with integers/naturals | Use Python floats alongside |
| Imports / dependencies | TLA+ is self-contained | Add imports to generated file |
| Class inheritance | TLA+ modules don't inherit | Compose classes manually |

### TLA+ features not yet supported by the compiler

| TLA+ feature | Status |
|--------------|--------|
| `EXTENDS Naturals, Sequences` | Parsed but not enforced |
| `CONSTANT` with model values | Parsed, placeholder value generated |
| Nested `IF/THEN/ELSE` | Not yet |
| `CHOOSE x \in S : P(x)` | Not yet |
| `\E x \in S : P(x)` (existential) | Not yet |
| `\A x \in S : P(x)` (universal) | Not yet |
| `LET ... IN` | Not yet |
| `CASE` expressions | Not yet |
| Set comprehension `{x \in S : P(x)}` | Not yet |
| Functions `[S -> T]` | Not yet |
| Records `[field |-> val]` | Not yet |
| PlusCal (`--algorithm`) | Not yet |
| Fairness (`WF_`, `SF_`) | Not yet |
| `INSTANCE` / module composition | Not yet |

## Official TLA+ resources

- [tlaplus/tlaplus](https://github.com/tlaplus/tlaplus) — TLC model checker + Toolbox IDE
- [tlaplus/CommunityModules](https://github.com/tlaplus/CommunityModules) — Extended standard library
- [tlaplus/Examples](https://github.com/tlaplus/Examples) — Real-world specs to learn from
- [tlaplus/PlusPy](https://github.com/tlaplus/PlusPy) — Run TLA+ specs in Python
- [tlaplus/apalache](https://github.com/tlaplus/apalache) — Symbolic model checker
