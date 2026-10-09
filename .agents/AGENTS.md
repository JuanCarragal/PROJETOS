# Project Rules

This file defines the project-scoped rules for the Antigravity agent in this workspace.

## Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations:

1. **Think Before Coding**:
   - Don't assume. Don't hide confusion. Surface tradeoffs.
   - Explicitly state assumptions before implementing. Ask if uncertain.
   - If multiple interpretations exist, present them instead of picking silently.

2. **Simplicity First**:
   - Minimum code that solves the problem. Nothing speculative.
   - No features, abstractions, or flexibility/configurability beyond what was requested.
   - If a solution is overcomplicated, simplify.

3. **Surgical Changes**:
   - Touch only what you must. Clean up only your own mess.
   - Match existing style. Do not refactor adjacent code that is not broken.

4. **Goal-Driven Execution**:
   - Define success criteria and loop until verified.
   - Translate tasks into verifiable goals (e.g. reproducing a bug in a test first).
