#!/bin/bash

for NOTEBOOK in *.ipynb; do
    PYDEVD_DISABLE_FILE_VALIDATION=1 jupyter nbconvert --Application.log_level=50 --to notebook --execute $NOTEBOOK || exit 1
done

exec "$@"