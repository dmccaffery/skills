#!/usr/bin/env sh
# Install the skills in this repo for agents that read raw SKILL.md directories
# (Codex CLI, OpenCode, Antigravity). Claude Code and Codex users should prefer
# the native plugin marketplaces — see README.md.
#
# Usage:
#   ./install.sh                       # project scope: ./.agents/skills/ in $PWD
#   ./install.sh --project DIR        # project scope in DIR
#   ./install.sh --global             # ~/.agents/skills + ~/.gemini/skills
#   ./install.sh --global --claude    # also ~/.claude/skills
#   ./install.sh --copy ...           # copy instead of symlink
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

mode=project
project_dir=$PWD
claude=false
copy=false

usage() {
  sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case $1 in
    --project)
      mode=project
      [ $# -ge 2 ] || { echo "error: --project requires a directory" >&2; exit 2; }
      project_dir=$2
      shift
      ;;
    --global) mode=global ;;
    --claude) claude=true ;;
    --copy) copy=true ;;
    -h | --help) usage ;;
    *) echo "error: unknown option: $1" >&2; usage 2 >&2 ;;
  esac
  shift
done

# Symlink (or copy) one skill directory into a target skills directory.
install_skill() {
  src=$1
  target_dir=$2
  name=$(basename "$src")
  mkdir -p "$target_dir"
  rm -rf "${target_dir:?}/${name:?}"
  if [ "$copy" = true ]; then
    cp -R "$src" "$target_dir/$name"
  else
    ln -s "$src" "$target_dir/$name"
  fi
  echo "installed $name -> $target_dir/$name"
}

if [ "$mode" = global ]; then
  set -- "$HOME/.agents/skills" "$HOME/.gemini/skills"
  [ "$claude" = true ] && set -- "$@" "$HOME/.claude/skills"
else
  set -- "$project_dir/.agents/skills"
  [ "$claude" = true ] && set -- "$@" "$project_dir/.claude/skills"
fi

found=false
for skill in "$repo_root"/plugins/*/skills/*/; do
  [ -f "$skill/SKILL.md" ] || continue
  found=true
  skill=${skill%/}
  for target in "$@"; do
    install_skill "$skill" "$target"
  done
done

if [ "$found" = false ]; then
  echo "error: no skills found under $repo_root/plugins/*/skills/" >&2
  exit 1
fi
