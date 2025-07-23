# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Testing:**
- `./test.sh` - Run unit tests using Python's unittest module
- `python -m unittest` - Alternative way to run tests

**Package Management:**
- `python -m pip install -e .` - Install package in development mode
- `./release-tag.sh` - Create and push version tag for releases (triggers CI/CD)

**Project Structure:**
- Uses `setuptools` with `pyproject.toml` configuration
- Entry point: `franklin = "franklin:franklin"` - CLI command defined in `src/franklin/__init__.py`

## Architecture

**Core CLI Framework:**
- Built with Click framework using plugin architecture
- Main CLI group defined in `src/franklin/__init__.py:franklin()` 
- Uses `AliasedGroup` for command aliases and `click-plugins` for extensibility
- Commands are organized into modules: `docker`, `jupyter`, `gitlab`, `update`

**Key Components:**
- `src/franklin/__init__.py` - Main CLI entry point and command registration
- `src/franklin/docker.py` - Docker container management 
- `src/franklin/jupyter.py` - Jupyter notebook integration
- `src/franklin/gitlab.py` - GitLab integration for exercise downloads
- `src/franklin/desktop.py` - Desktop/system integration (Docker Desktop setup)
- `src/franklin/config.py` - Configuration management
- `src/franklin/utils.py` - Shared utilities

**Package Distribution:**
- Three-tier conda package system: `franklin` (students) → `franklin-educator` (educators) → `franklin-admin` (admin)
- Template system in `src/franklin/data/templates/` for exercise scaffolding
- Uses Pixi for dependency management in exercises

**Exercise System:**
- Exercise templates include Docker configuration, pixi.toml, and Jupyter notebooks
- Template exercises use `pixi run test-notebook` to execute and validate notebooks
- Supports automatic dependency collection from notebook imports

## Commit Convention

Use conventional commits format: `<type>[optional scope]: <description>`
- `feat:` - new features (MINOR version)
- `fix:` - bug fixes (PATCH version) 
- `BREAKING CHANGE:` footer or `!` suffix for breaking changes (MAJOR version)