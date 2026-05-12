# Text is Thought, and Thought is Holy

Source: https://r.jina.ai/https://danielmiessler.com/blog/text-is-thought-holy
Original author: Daniel Miessler
Published: 2026-05-08
Source type: community / practitioner response
Confidence: confirmed from fetched source

## Core Claim

Markdown should remain the primary spec and thought format because text is close to thought: it is easy to inspect, edit, diff, and refine directly. HTML is useful, but making HTML the primary spec format risks separating humans from the thinking and writing process.

## Agreement With HTML-First Argument

- Long text files can be hard to read and share.
- Formatting, images, hierarchy, and interfaces can make ideas easier to communicate.
- Rich presentation files are valuable for persuasion, review, and cross-functional communication.

## Disagreement

The objection is not to HTML itself. The objection is replacing the primary editable thought artifact with HTML.

| Format | Strength | Weakness |
|---|---|---|
| Markdown | Easy for humans and agents to write, edit, diff, and reason about | Harder to read and share when long |
| HTML | Easy to present, browse, share, and enrich visually | Harder to hand-edit and review in version control |

## Document Pairing Proposal

Use paired documents instead of choosing one format:

1. Markdown or MDX remains the authoritative thought/source file.
2. HTML is generated as a linked presentation file.
3. Humans and agents edit the Markdown source.
4. The HTML companion can be regenerated or refreshed after the source changes.

## Repository Takeaway

Adopt "Markdown SSOT + HTML companion" as the rule for skills:

- Markdown carries canonical decisions, requirements, boundaries, and recommendations.
- HTML carries rich presentation, visualization, interaction, and shareability.
- HTML must not silently become the only place where the real plan or decision lives.
- If the two diverge, update the Markdown source first, then regenerate or revise the companion.
