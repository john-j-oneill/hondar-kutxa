# Strata on Unraid

There is no Community Applications template for
[Strata](https://github.com/Niko1221/Strata), but upstream ships a
`Dockerfile` (NVIDIA only). There's also no published image, so the image
has to be built on the server. This folder has:

- `build.sh`: downloads Strata and builds `strata:latest` on the server
- `my-strata.xml`: an Unraid container template that runs that image

Target box: RTX 5060 Ti 16 GB (sm_120), 64 GB DDR4, 512 GB NVMe cache pool,
also running Plex. Running there with IQ3_XXS.

## Storage: keep the NVMe as the cache pool

You don't need to change the cache pool. In Unraid the cache pool *is* where
container data belongs: `appdata`, `system` (docker.img) and `domains` live
there by default. Strata just needs its files on that pool and kept off the
array:

- The model's 28.8 GB n-gram table is read **at random** on every token.
  Parity-protected spinning disks can't keep up with that, and prompts stall
  for minutes (upstream issue #605).
- Map the data path as **`/mnt/cache/appdata/strata`**, not
  `/mnt/user/appdata/strata`. `/mnt/user` goes through Unraid's FUSE layer
  (shfs), which slows random reads and can't do the direct I/O Strata uses.
- Check *Shares → appdata*: **Primary storage = Cache**, and Secondary storage
  = **None**. Otherwise make sure the mover direction is Array → Cache. Either
  way, the mover will never shift the model onto the array.

Space on the 512 GB NVMe:

| What | Size |
| --- | ---: |
| Model + pack + MTP layer (`/mnt/cache/appdata/strata`) | ~80 GB per model |
| `strata:latest` image (CUDA 13 devel base + engine) | ~15 GB |
| Build cache during `build.sh` (pruned at the end) | a few GB |
| Source checkout (`/mnt/cache/appdata/strata-src`) | < 50 MB |

**docker.img is 20 GB by default, and that's too small** for the image plus
your other containers. Under *Settings → Docker*, stop Docker and either
raise the vDisk size to 60 GB or more, or switch to *Docker data-root:
directory*. Then start it again.

## 1. GPU driver

1. *Apps* → install **Nvidia Driver** (ich777).
2. On its settings page, select a driver **580 or newer** (Strata's image
   is CUDA 13.0), then reboot.
3. Confirm with `nvidia-smi` in the Unraid terminal.

## 2. Build the image

In the Unraid terminal (or as a User Scripts script, run in the background):

```sh
mkdir -p /mnt/cache/appdata/strata
curl -fsSLo /mnt/cache/appdata/strata/build.sh \
  https://raw.githubusercontent.com/john-j-oneill/hondar-kutxa/main/unraid/strata/build.sh
bash /mnt/cache/appdata/strata/build.sh
```

(That URL works once this is merged to `main`. Before then, copy `build.sh`
over by hand.)

The build defaults to `CUDA_ARCHITECTURES=120`, the RTX 5060 Ti only,
which is much faster than upstream's five-arch default. Expect roughly
20–60 minutes depending on the CPU. No GPU is used during the build.

Upstream's Dockerfile needs BuildKit (it uses a `RUN` heredoc). Unraid's
Docker has no `buildx` plugin, so `build.sh` runs the build from the
official `docker:cli` image, which has buildx, against the host's daemon.

## 3. Add the container

```sh
cp /path/to/my-strata.xml /boot/config/plugins/dockerMan/templates-user/
```

Then *Docker → Add Container → Template: strata*, check the values, and
*Apply*. The template sets:

- `--runtime=nvidia` and `NVIDIA_VISIBLE_DEVICES=all` (the Unraid Nvidia
  plugin's convention, instead of `--gpus all`)
- `--ulimit memlock=-1:-1`, because Strata pins part of its RAM for the GPU
- `/data` → `/mnt/cache/appdata/strata`
- host port **8642** → container port 8080 (see [Port](#port))
- an **API key**, required (see [API key](#api-key))
- `MODEL=IQ3_XXS`, `FAMILY=qwen`, `CONTEXT=32768`. See
  [Which size](#which-size).
- `VISION=cpu`: pictures work, but the encoder runs on the CPU, so no VRAM
  goes to it. On the GPU (`yes`), ~1.4 GB of VRAM is held back for it,
  leaving fewer experts cached and making text a few % slower. The price on
  the CPU is ~3–13 s per picture (more for big or detailed images), and
  about 1 GB of RAM for the encoder. `no` skips it entirely.

Leave *Reinstall* at `0`. The first start notices there's no config on
`/data` and runs setup by itself. It downloads ~83 GB (model, MTP layer,
vision encoder), prepares the pack, then loads 35–55 GB into RAM (1–3 min).
The container shows *healthy* once the model is up. Then open
`http://<unraid-ip>:8642`.

**The log goes quiet during the download.** That's expected. Strata redraws
its progress line in place with `\r` and only ends it when a file is done.
Docker's log shows only finished lines, and the first shard is ~40 GB. To see
it moving:

```sh
watch -n 5 du -sh /mnt/cache/appdata/strata/models/IQ3_XXS/
```

A growing `*.gguf.part` means it's working. On gigabit it all takes ~12
minutes. If nothing grows, test the container's connection:
`docker exec strata curl -sI https://huggingface.co | head -1`.

If *Apply* fails trying to pull `strata:latest` from Docker Hub, run it
from the terminal instead (same settings):

```sh
docker run -d --name strata --restart unless-stopped \
  --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  --ulimit memlock=-1:-1 -p 8642:8080 \
  -v /mnt/cache/appdata/strata:/data \
  -e API_KEY=<your key> \
  -e MODEL=IQ3_XXS -e FAMILY=qwen -e CONTEXT=32768 -e VISION=cpu \
  strata:latest
```

## Which size

The size is mostly a RAM budget. Strata's RAM is locked, so Unraid can't
reclaim it under pressure. A container that runs short gets killed; it
doesn't just slow down.

| | IQ2_XS | IQ3_XXS |
| --- | --- | --- |
| RAM Strata takes | ~42 GB | ~49 GB |
| Left of 64 GB | ~22 GB | ~15 GB |
| Decode (upstream's RTX 5070 box) | 79 tok/s | 62 tok/s |
| Download | 68 GB | 76 GB |
| Upstream's quality label | better | great |

This box used ~3.6 GB before Strata (Unraid + Plex), so IQ3_XXS fits with
room to spare. On a busier server, take IQ2_XS. DDR4 probably widens the speed gap a
little, because IQ3_XXS does more of its work on the CPU. Switching later
only needs a different *Model size*: both fit on the NVMe side by side.

## Sharing the GPU with Plex

If Plex also uses the 5060 Ti for hardware transcoding (`--runtime=nvidia` on
the Plex container), it competes with Strata for VRAM. Strata fills the card
with its expert cache, so a transcode that starts later can fail or fall
back to the CPU. Once Strata is up, go to *About → Model settings* in its web
page, set **VRAM reserve** to ~`1536` MiB, and restart the container. Each
transcode needs a few hundred MB. Text gets slightly slower, because fewer
experts fit on the card.

Plex transcoding to RAM (`/tmp` or `/dev/shm`) also eats into the headroom
in the table above.

## Port

Strata always listens on 8080 *inside* the container. Only the host side of
the mapping matters, and 8080 is a popular default (qBittorrent, UniFi, many
web UIs), so the template maps it to **8642**. To use another port, change
*Web UI / API port* in the template. Leave the container port at 8080; don't
add a `PORT` variable.

## API key

Strata is reachable from your whole LAN, so give it a key. Without one,
anything on the network can use the GPU and read the chats it keeps in
memory.

1. Generate one in the Unraid terminal: `openssl rand -hex 24`
2. Paste it into the template's **API key** field (masked) *before the
   first start*. Setup writes it into the model's config on `/data`.
3. To change it later: new value, *Reinstall* = `1`, apply, wait for the
   container to come up, then *Reinstall* back to `0`.

Clients send it the usual way: `Authorization: Bearer <key>` (OpenAI style)
or `x-api-key: <key>` (Anthropic style). Any app's "API key" field does the
right thing. `/health` stays open without the key, so Unraid's health check
keeps working.

## Using it from other PCs

- **Browser:** `http://<unraid-ip>:8642`. The page shows *API key needed*.
  Enter the key under *About → Settings → API key*. It's saved in that
  browser only, so do this once per browser.
- **OpenAI-compatible apps** (Open WebUI, Continue, Cline, …): base URL
  `http://<unraid-ip>:8642/v1`, API key = your key, any model name.
- **Claude Code:**
  ```sh
  export ANTHROPIC_BASE_URL=http://<unraid-ip>:8642
  export ANTHROPIC_AUTH_TOKEN=<your key>
  ```
- **Codex CLI / Responses API apps:** `http://<unraid-ip>:8642/v1` (they use
  `/v1/responses`).

Give the server a static IP or a DHCP reservation in your router, so the URL
doesn't change. Plain HTTP is fine on your LAN. To reach it from outside,
don't port-forward. Use Tailscale (there's an Unraid plugin), or put it
behind a reverse proxy with HTTPS. The key goes over the wire in clear text
otherwise.

## Changing things later

- **Update Strata:** run `build.sh` again, then restart the container. The
  model on `/data` is kept.
- **Context / vision / API key:** change the value, set *Reinstall* to `1`,
  apply, wait for it to come up, then set *Reinstall* back to `0`.
- **Another model:** change *Model size* / *Model family*. A model that isn't
  on `/data` yet gets downloaded (another ~70 GB). Models already there just
  switch over.
- **Keep a copy** on the array, in case the upstream files move or vanish.
  Stop the container first, and make sure the `backups` share is array-only:
  ```sh
  rsync -a --info=progress2 /mnt/cache/appdata/strata/ /mnt/user/backups/strata/data/
  docker save strata:latest | gzip > /mnt/user/backups/strata/strata-image.tar.gz
  tar czf /mnt/user/backups/strata/strata-src.tar.gz -C /mnt/cache/appdata strata-src
  ```
  To restore, copy `data/` back and `docker load < strata-image.tar.gz`. The
  `.done` marks come along, so setup downloads nothing.
- Unraid's "update available" check shows *not available* for this container,
  because the image is local. That's expected.
