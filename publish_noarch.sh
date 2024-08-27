#!/usr/bin/env bash

set -e

git status --porcelain

source ~/miniconda3/etc/profile.d/conda.sh

conda activate condabuild

gh release create --latest -p v$(python setup.py --version)

cd conda-build

conda build .

cd ..

conda deactivate
