#!/usr/bin/env bash
set -euo pipefail

target=out/ci-tools
mkdir -p "$target"
for tool in "$@"; do
  case "$tool" in
    actionlint)
      repo=rhysd/actionlint
      version=1.7.12
      archive=actionlint_1.7.12_linux_amd64.tar.gz
      digest=8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8
      ;;
    gitleaks)
      repo=gitleaks/gitleaks
      version=8.30.1
      archive=gitleaks_8.30.1_linux_x64.tar.gz
      digest=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
      ;;
    *) echo "Unsupported tool: $tool" >&2; exit 2 ;;
  esac
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location --retry 3 \
    --max-time 90 --output "$target/$archive" "https://github.com/$repo/releases/download/v$version/$archive"
  printf '%s  %s\n' "$digest" "$target/$archive" | sha256sum --check
  tar -xzf "$target/$archive" -C "$target" "$tool"
done
