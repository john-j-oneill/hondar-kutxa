#!/bin/bash
# Build the Strata image on the Unraid server, from upstream's own Dockerfile.
#
#   bash build.sh            # RTX 50 only (sm_120: the RTX 5060 Ti)
#   bash build.sh "89;120"   # add RTX 40, etc.
#   STRATA_REF=v0.1.43.1 bash build.sh   # a release tag instead of main
#
# Run it again to pick up a newer Strata; the model on the /data volume is kept.
set -euo pipefail

ARCHS="${1:-120}"
SRC="${STRATA_SRC:-/mnt/cache/appdata/strata-src}"
REF="${STRATA_REF:-main}"

echo "Fetching Strata ($REF) into $SRC"
rm -rf "$SRC"
mkdir -p "$SRC"
curl -fsSL "https://github.com/Niko1221/Strata/archive/$REF.tar.gz" \
  | tar xz -C "$SRC" --strip-components=1

# Upstream's Dockerfile uses a RUN heredoc, which only BuildKit understands.
# Unraid's docker has no buildx plugin, so plain `docker build` falls back to
# the legacy builder and fails. The official docker:cli image ships buildx;
# run the build from it against the host's daemon instead.
docker_bk() {
  if docker buildx version >/dev/null 2>&1; then
    docker "$@"
  else
    docker run --rm \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v "$SRC":/src:ro \
      docker:cli "$@"
  fi
}
src_path="$SRC"
docker buildx version >/dev/null 2>&1 || src_path=/src
docker_bk build -t strata:latest --build-arg "CUDA_ARCHITECTURES=$ARCHS" "$src_path"

# Clear the build cache (intermediate layers, often GBs). It belongs to the
# same BuildKit as the build, hence docker_bk. The previous strata image
# can't go yet: the running container still uses it.
docker_bk builder prune -af
docker image prune -f
echo "Built strata:latest. Recreate the container (Docker > strata > Edit > Apply;"
echo "a restart keeps the old image), then run: docker image prune -f"
