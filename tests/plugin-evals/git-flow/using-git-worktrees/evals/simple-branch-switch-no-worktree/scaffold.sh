#!/usr/bin/env bash
# Two ordinary local branches, clean tree, no parallel work in play.
set -euo pipefail

git init -q .
git config user.email "eval@example.com"
git config user.name "Eval Runner"
git symbolic-ref HEAD refs/heads/main

printf '# shop\n\nOnline shop app.\n' >README.md
git add README.md
git commit -q -m "initial commit"

git branch feature-a
git branch feature-b
git switch -q feature-a
