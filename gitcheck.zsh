#!/bin/zsh
set -euo pipefail

echo "=== SYSTEM ==="
sw_vers 2>/dev/null || true
echo "Shell: $SHELL"
echo "User: $(whoami)"
echo "PWD:  $(pwd)"
echo

echo "=== DIRECTORY OVERVIEW (top level) ==="
ls -la
echo

echo "=== DISK USAGE (top level, largest 20) ==="
du -sh ./* 2>/dev/null | sort -hr | head -n 20 || true
echo

echo "=== GIT: BASIC STATUS ==="
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Git repo: YES"
  echo
  echo "--- git status (short) ---"
  git status -sb
  echo
  echo "--- remotes ---"
  git remote -v || true
  echo
  echo "--- branches ---"
  git branch -vv || true
  echo
  echo "--- last 10 commits ---"
  git --no-pager log --oneline -n 10 || true
  echo
  echo "--- .gitignore (if present) ---"
  if [ -f .gitignore ]; then
    sed -n '1,200p' .gitignore
  else
    echo "(no .gitignore found)"
  fi
  echo
  echo "--- ignored files sample (first 50) ---"
  git ls-files -oi --exclude-standard | head -n 50 || true
  echo
  echo "--- tracked files count ---"
  echo "Tracked files: $(git ls-files | wc -l | tr -d ' ')"
  echo
  echo "--- largest tracked files (top 20) ---"
  git ls-files -z | xargs -0 -I{} bash -lc 'wc -c "{}" 2>/dev/null | awk "{print $1 "\t" "{}"}"' \
    | sort -nr | head -n 20 || true
else
  echo "Git repo: NO"
  echo "Tip: In GitHub Desktop, choose 'Add Local Repository…' or initialize a repository here."
fi

echo
echo "=== PROJECT QUICK CHECKS ==="
for f in README.md README LICENSE package.json pyproject.toml requirements.txt Pipfile Gemfile go.mod Cargo.toml; do
  if [ -f "$f" ]; then
    echo "FOUND: $f"
  fi
done
echo
echo "--- upstream tracking ---"
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "(no upstream set)"

echo "=== SECRETS QUICK SCAN (basic patterns) ==="
echo "This scans text in tracked files only for obvious key patterns (best-effort)."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git ls-files -z \
  | xargs -0 grep -nI -E \
    '(api[_-]?key|secret|token|authorization: bearer|BEGIN (RSA|OPENSSH) PRIVATE KEY|aws(_|-)?secret|aws(_|-)?access|x-api-key|client_secret|private_key)' \
    2>/dev/null \
  | head -n 200 || echo "(no matches in tracked files)"
else
  echo "(not a git repo, skipping tracked-file scan)"
fi

echo
echo "=== DONE ==="
