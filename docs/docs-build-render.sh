#!/usr/bin/env bash

rm -f api/_styles-quartodoc.css api/_sidebar.yml *.qmd
quartodoc build && quartodoc interlinks && quarto render
