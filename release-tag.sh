#!/usr/bin/env bash

if [[ `git status --porcelain` ]]; then
  RED='\033[0;31m'
  NC='\033[0m' # No Color
  echo -e "${RED}Changes to pyproject.toml must be pushed first.${NC}"
  echo "Changes to pyproject.toml must be pushed first."
else
  v=$(python setup.py --version) || exit
  git tag -a "v${v}" -m "${1:-Release}" && git push origin --tags
fi