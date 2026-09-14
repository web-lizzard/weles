#!/usr/bin/env bash
set -euo pipefail

sha="${1:?usage: remote-deploy.sh <sha>}"

compose_file="/srv/weles/compose.yml"
deployed_sha_file="/srv/weles/deployed_sha"
tunnel_env_file="/srv/weles/cloudflared.env"

previous=""
if [ -f "$deployed_sha_file" ]; then
  previous="$(cat "$deployed_sha_file")"
fi

prune_old_tags() {
  local keep_sha="$1"
  local keep_previous="$2"
  docker images weles-api --format '{{.Tag}}' | while IFS= read -r tag; do
    if [ "$tag" != "$keep_sha" ] && [ "$tag" != "$keep_previous" ]; then
      docker rmi "weles-api:$tag" || true
    fi
  done
}

# The tunnel never decides a deploy: the API is already switched when it runs.
start_tunnel() {
  local tag="$1"
  if [ ! -f "$tunnel_env_file" ]; then
    echo "tunnel not configured, skipping cloudflared"
    return 0
  fi
  if ! WELES_API_TAG="$tag" docker compose -f "$compose_file" --profile tunnel up -d cloudflared; then
    echo "::warning::cloudflared failed to start; the public address is down"
    return 0
  fi
  WELES_API_TAG="$tag" docker compose -f "$compose_file" --profile tunnel ps cloudflared || true
}

if WELES_API_TAG="$sha" docker compose -f "$compose_file" up -d --wait --wait-timeout 120 api; then
  echo "$sha" >"$deployed_sha_file"
  prune_old_tags "$sha" "$previous"
  start_tunnel "$sha"
  exit 0
fi

echo "::error::deploy of $sha failed health checks" >&2

if [ -n "$previous" ]; then
  echo "::error::rolling back to $previous" >&2
  WELES_API_TAG="$previous" docker compose -f "$compose_file" up -d --wait --wait-timeout 120 api
fi

exit 1
