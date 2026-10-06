#!/bin/bash
# Build the Strata image on the Unraid server, from upstream's own Dockerfile.
#
#   bash build.sh            # RTX 50 only (sm_120: the RTX 5060 Ti)
#   bash build.sh "89;120"   # add RTX 40, etc.
#
# Run it again to pick up a newer Strata; the model on the /data volume is kept.
set -euo pipefail

ARCHS="${1:-120}"
SRC="${STRATA_SRC:-/mnt/cache/appdata/strata-src}"
REF="${STRATA_REF:-main}"

echo "Fetching Strata ($REF) into $SRC"
rm -rf "$SRC"
mkdir -p "$SRC"
curl -fsSL "https://github.com/Niko1221/Strata/archive/refs/heads/$REF.tar.gz" \
  | tar xz -C "$SRC" --strip-components=1

# Upstream's Dockerfile uses a RUN heredoc, which only BuildKit understands.
# Unraid's docker has no buildx plugin, so plain `docker build` falls back to
# the legacy builder and fails. The official docker:cli image ships buildx;
# run the build from it against the host's daemon instead.
build_args=(build -t strata:latest --build-arg "CUDA_ARCHITECTURES=$ARCHS")
if docker buildx version >/dev/null 2>&1; then
  docker "${build_args[@]}" "$SRC"
else
  docker run --rm \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$SRC":/src:ro \
    docker:cli "${build_args[@]}" /src
fi

# drop the previous strata image and the build cache
docker image prune -f
docker builder prune -f >/dev/null 2>&1 || true
echo "Built strata:latest. Start or restart the container in Unraid's Docker tab."
