# AI one-shots

Small, self-contained projects written by AI coding assistants, mostly from a
single prompt, with at most a few follow-up corrections. Each one lives in its
own folder; this file records the prompt each started from, the model that
wrote it, and what it cost where that's known.

## Running them

Most are static web pages. Some browsers won't load ES modules from `file://`,
so serve the folder you want to view, for example:

```sh
npx serve ai-oneshots/pagoda-garden
```

## Projects

### [`pagoda-garden/`](pagoda-garden/)

Voxel Japanese garden in Three.js: a 5-tier pagoda, torii, cherry trees, a pond
with an arched bridge and stone lanterns, on a grass island lit by a sunset.

![Pagoda garden](pagoda-garden/screenshot.png)

**Prompt:**

> Make a small voxel Pagoda Garden scene in Three.js. One file index.html,
> Three.js + OrbitControls from CDN via import map. Everything from cubes on a
> grass island: 5-tier pagoda (dark roofs, red columns), red torii, 2–3 cherry
> trees, pond with wooden bridge, a couple of stone lanterns. Warm sunset light
> with shadows, slowly auto-rotating orbit camera. Only standard Three.js
> materials, no custom shaders. Keep it simple and make it work.

**Follow-ups:** one. *"The bridge is over the largest dim of the pond, which is
silly. And while there's a path the bridge doesn't connect to it on either
end."*

| | |
| --- | --- |
| Model | Claude Opus 5.5, medium effort |
| Harness | Claude Code 2.1.291, cloud session on claude.ai |
| Date | 2026-10-06 |
| Wall time | ~4 min to the first commit, ~11 min including the bridge fix |
| Output tokens | 22,030 |
| Input tokens | 566 uncached, 64,698 cache writes, 2,555,004 cache reads |
| Peak context | ~107k tokens |
| Cost | ~$1.47 (API-equivalent, as reported by the session) |

The token and cost figures are cumulative for the whole session, so they also
include moving the project into this folder and writing these READMEs, which
were a small share of the total. Most of the cache-read volume comes from
re-sending the conversation on each tool call, including the screenshots taken
to check the render.
