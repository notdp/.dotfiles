# Using Claude Code: The Unreasonable Effectiveness of HTML

Source: https://r.jina.ai/https://x.com/trq212/status/2052809885763747935
Original author: Thariq Shihipar
Published: 2026-05-12
Source type: community / practitioner article
Confidence: confirmed from fetched source

## Core Claim

HTML is often a better presentation surface than Markdown for complex agent outputs because it can combine structure, visual hierarchy, CSS, SVG, images, diagrams, layout, and interaction in one shareable browser-native artifact.

## Why It Matters

- Long Markdown files are easy to generate but hard to review, especially beyond about 100 lines.
- HTML can present the same underlying ideas with tabs, grids, annotations, diagrams, responsive layout, and interactive controls.
- Agents can use codebase context, browser context, MCP sources, and git history to synthesize rich HTML explainers or reports.
- HTML makes it easier to share specs, reports, PR explainers, and design explorations with people who will not read a long raw text file.

## Useful Scenarios

| Scenario | HTML value |
|---|---|
| Implementation plan | Mockups, data flow, diagrams, important snippets, side-by-side review |
| PR explainer | Rendered diff, inline annotations, severity colors, concept diagrams |
| Design exploration | Multiple visual directions, sliders, interaction prototypes |
| Research report | Visual synthesis across sources, diagrams, slide/deck-like reading |
| Throwaway editor | Drag/drop, forms, validation, copy-as-JSON / copy-as-prompt export |

## Caveats

- The author explicitly warns against prematurely turning the idea into a generic `/html` skill.
- The value is not "HTML everywhere"; the value is knowing what the artifact should help the human do.
- HTML can take longer to generate and produces noisier diffs than Markdown.
- HTML is less convenient for direct human editing and version review.

## Repository Takeaway

Use this as evidence for an output-surface decision rule:

1. Keep short decisions and authoritative specs in Markdown.
2. Add an HTML companion when the output is long, visual, shareable, or interactive.
3. Link the HTML companion back to the Markdown source so the artifact does not become a competing source of truth.
