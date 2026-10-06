# AI one-shots

Small, self-contained projects written by AI coding assistants, mostly from a
single prompt, with at most a few follow-up corrections. Each one lives in its
own folder, and the table below records the prompt it started from.

| Project | Description | Original prompt |
| --- | --- | --- |
| [`pagoda-garden/`](pagoda-garden/) | Voxel Japanese garden in Three.js: a 5-tier pagoda, torii, cherry trees, a pond with an arched bridge and stone lanterns, on a grass island lit by a sunset. | *"Make a small voxel Pagoda Garden scene in Three.js. One file index.html, Three.js + OrbitControls from CDN via import map. Everything from cubes on a grass island: 5-tier pagoda (dark roofs, red columns), red torii, 2–3 cherry trees, pond with wooden bridge, a couple of stone lanterns. Warm sunset light with shadows, slowly auto-rotating orbit camera. Only standard Three.js materials, no custom shaders. Keep it simple and make it work."* Follow-up: the bridge should cross the pond's narrow width and connect to the path. |

## Running them

Most are static web pages. Some browsers won't load ES modules from `file://`,
so serve the folder you want to view, for example:

```sh
npx serve ai-oneshots/pagoda-garden
```

![Pagoda garden](pagoda-garden/screenshot.png)
