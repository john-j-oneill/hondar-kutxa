# Strata on Unraid

There is no Community Applications template for
[Strata](https://github.com/Niko1221/Strata), but upstream ships a
`Dockerfile` (NVIDIA only). There's also no published image, so the image
has to be built on the server. This folder has:

- `build.sh`: downloads Strata and builds `strata:latest` on the server
- `my-strata.xml`: an Unraid container template that runs that image

Target box: RTX 5060 Ti 16 GB (sm_120), 64 GB RAM, 512 GB NVMe cache pool.

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
- `MODEL=IQ2_XS`, `FAMILY=qwen`, `CONTEXT=32768`, `VISION=no`. IQ2_XS is
  upstream's pick for 64 GB. IQ3_XXS / IQ3_S also fit, but they're slower
  and leave less RAM for Unraid and the other containers.

The first start downloads ~70 GB, then loads 35–55 GB into RAM (1–3 min).
Follow it in the container log. The container shows *healthy* once the model
is up. Then open `http://<unraid-ip>:8080`.

If *Apply* fails trying to pull `strata:latest` from Docker Hub, run it
from the terminal instead (same settings):

```sh
docker run -d --name strata --restart unless-stopped \
  --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all \
  --ulimit memlock=-1:-1 -p 8080:8080 \
  -v /mnt/cache/appdata/strata:/data \
  -e MODEL=IQ2_XS -e FAMILY=qwen -e CONTEXT=32768 -e VISION=no \
  strata:latest
```

## Using it

- Browser: `http://<unraid-ip>:8080`
- OpenAI-compatible apps: base URL `http://<unraid-ip>:8080/v1`
- Claude Code / Anthropic API apps: `ANTHROPIC_BASE_URL=http://<unraid-ip>:8080`

Set **API key** in the template before you expose the port beyond your LAN.

## Changing things later

- **Update Strata:** run `build.sh` again, then restart the container. The
  model on `/data` is kept.
- **Context / vision / API key:** change the value, set *Reinstall* to `1`,
  apply, wait for it to come up, then set *Reinstall* back to `0`.
- **Another model:** change *Model size* / *Model family*. A model that isn't
  on `/data` yet gets downloaded (another ~70 GB). Models already there just
  switch over.
- Unraid's "update available" check shows *not available* for this container,
  because the image is local. That's expected.
