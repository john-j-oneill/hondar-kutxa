# Pagoda garden: Strata, thinking high

The same pagoda garden prompt, run locally in Strata on an older desktop with
thinking set to high. See [`../Strata-thinking-low/`](../Strata-thinking-low/)
for the same model with thinking set to low.
It needed three follow-up prompts to fix bugs before it ran.

![Strata pagoda garden](screenshot.png)

## Model and engine

| | |
| --- | --- |
| Model | qwen3.8-flash-next-iq3_xxs |
| Thinking | high |
| Engine | v0.1.40 |
| Context | 131,072 tokens |
| KV cache | 8-bit, all in VRAM |
| Experts in VRAM | 3,920 (6.6 GB) |
| Speculation | MTP drafts up to 3 tokens, prompt lookup on |
| Images | off |

## This PC

| | |
| --- | --- |
| GPU | NVIDIA TITAN V + NVIDIA GeForce GTX 1080 Ti, 23 GB |
| CPU | Intel Core i9-7900X @ 3.30 GHz, 20 threads |
| RAM | 62 GB |

## Follow-up prompts

1. *"At least on Firefox it sits there saying "Stacking Cubes" and a loading bar
   goes back and forth but nothing ever happens"*
2. ```
   ReferenceError: r is not defined
       buildPagoda file:///home/honeywell/Downloads/index-strata.html:589
       main file:///home/honeywell/Downloads/index-strata.html:606
       <anonymous> file:///home/honeywell/Downloads/index-strata.html:989
   ```
3. ```
   TypeError: c.getHexString is not a function
       css file:///home/honeywell/Downloads/index-strata.html:358
       drawSky file:///home/honeywell/Downloads/index-strata.html:372
       updateSun file:///home/honeywell/Downloads/index-strata.html:410
       main file:///home/honeywell/Downloads/index-strata.html:892
       <anonymous> file:///home/honeywell/Downloads/index-strata.html:989
   ```

## Run stats

| Started | Turn | Prompt | Reused | Output | Tok/s | VRAM hit rate | Duration |
| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |
| 12:33:06 PM | Original prompt | 155 | 0 | 73,328 | 34.8 | 66.8% +1.1% PCIe | 2,114.9 s |
| 01:12:04 PM | Follow-up 1 | 17,969 | 150 | 29,716 | 37.8 | 63.7% +1.4% PCIe | 1,032.3 s |
| 01:33:39 PM | Follow-up 2 | 36,686 | 17,964 | 2,630 | 36.1 | 61.3% +1.6% PCIe | 403.8 s |
| 01:44:06 PM | Follow-up 3 | 37,600 | 36,681 | 483 | 34.0 | 58.2% +1.6% PCIe | 31.2 s |
| | **Total** | **92,410** | **54,795** | **106,157** | | | **3,582.2 s** |

That's about 60 minutes of generation, 35 of them on the first answer, and
about 71 minutes of wall-clock time from the first prompt to the last answer,
including time spent testing between turns. 37,615 prompt tokens were
processed fresh; the rest were reused from cache. No API cost, since it ran
locally.
