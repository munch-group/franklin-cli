#!/usr/bin/env bash

if [[ `git status --porcelain` ]]; then
  echo "Changes to pyproject.toml must be pushed first."
else
  v=$(python setup.py --version)
  git tag -a "v${v}" -m "${1:-Release}" && git push origin --tags
fi