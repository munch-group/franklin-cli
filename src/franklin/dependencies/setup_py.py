#!/usr/bin/env python3
"""
Setup script for Development Environment Installer
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text() if (this_directory / "README.md").exists() else ""

setup(
    name="dev-env-installer",
    version="1.0.0",
    author="Development Team",
    author_email="dev@example.com",
    description="Automatically install missing development tools (Miniforge, Pixi, Docker, Chrome)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/dev-env-installer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.7",
    install_requires=[
        # No external dependencies - uses only standard library
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.800",
        ]
    },
    entry_points={
        "console_scripts": [
            "dev-env-installer=dev_env_installer:main",
            "install-dev-env=dev_env_installer:main",
        ],
    },
    py_modules=["dev_env_installer"],
    include_package_data=True,
    zip_safe=False,
    keywords="development environment installer miniforge pixi docker chrome automation",
    project_urls={
        "Bug Reports": "https://github.com/your-org/dev-env-installer/issues",
        "Source": "https://github.com/your-org/dev-env-installer",
        "Documentation": "https://github.com/your-org/dev-env-installer/blob/main/README.md",
    },
)