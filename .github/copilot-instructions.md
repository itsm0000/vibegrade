Read the AGENTS.md file in this repository. Follow all rules defined there.
Before starting work, read HANDOFF.md. Before making architecture decisions, read docs/DECISIONS.md.

Key rules:
- Never suggest lazy/default tech — research industry standards first
- All testing by adversarial sub-agent
- Every session ends with HANDOFF.md updated + commit + push
- Expensive models = planning only; cheap models = generation + testing

AI Commands (execute immediately, no confirmation):
- "morning brief" → read all project HANDOFF.md files, display status dashboard
- "wrap up" → update HANDOFF.md, commit, push
- "capture idea: [text]" → append to OMNI-HELPER/IDEAS.md
