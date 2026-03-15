# fran++ insights

Ongoing design notes and realizations.

## LLMs are part of the language

The compiler isn't just a syntax transformer. LLMs play a role:

- User says "fizzbuzz" → LLM knows the algorithm → emits compressed form: `divisors {3: "Fizz", 5: "Buzz"}`
- The compressed form is what fran++ actually compiles to Python
- The pipeline: **English → (LLM) → fran++ → (compiler) → Python**

Without the LLM, fran++ is just another syntax. With it, English becomes the input language.

## Compression = separating the idea from the machinery

FizzBuzz is not an if/elif chain. It's a rule: `{3: "Fizz", 5: "Buzz"}`. The if/elif chain is machinery that implements the rule. fran++ should express rules, not machinery.

Good compression: `divisors {3: "Fizz", 5: "Buzz"}`
Bad compression: same logic with fewer characters

The test: can you look at the fran++ code and immediately see the **decision** without reading the **implementation**?

## State machines aren't always the right abstraction

v0.0.1 forced everything into state machines (TLA+ style). That works for:
- Things that change over time
- Rules about what's allowed/forbidden
- Concurrent processes

It doesn't work for:
- Pure expressions (`1 + 3 + 5`)
- Simple transformations (fizzbuzz)
- Anything where there's no meaningful "state"

fran++ should use the simplest abstraction that fits. Expressions when possible, state machines only when needed.

## Rules and goals, not steps

The most powerful thing TLA+ does is NOT describing an algorithm step by step (that's just Python with different syntax). It's powerful **when it describes rules and goals and lets the machine figure out the steps.**

DieHard example: you don't write "fill big, pour into small, empty small..." — you write "here are the jugs, here are the allowed moves, find me 4 gallons." The model checker explores every possible path and finds the solution.

fran++ should work the same way: you state what's true, what's allowed, and what you want. The machine does the rest.

## What fran++ is NOT

- Not just Python with different syntax (that adds nothing)
- Not a replacement for LLMs (they're a collaborator, not a competitor)
- Not a verification tool only (TLA+ already does that)

## Open questions

- What's the right level of compression? Too compressed = unreadable. Too verbose = just Python.
- How does the LLM know which fran++ constructs to emit? Does fran++ need a standard library of patterns (divisors, accumulators, state machines)?
- Where exactly does verification fit? Is it automatic, optional, or the whole point?
