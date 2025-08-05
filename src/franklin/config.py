
"""
Configuration settings for the Franklin package.

This module contains all configuration parameters used throughout the Franklin
ecosystem, including GitLab integration settings, Docker configuration, and
UI preferences.

Attributes
----------
name : str
    The name of the package.
maintainer_email : str
    Email address of the package maintainer.
gitlab_domain : str
    Domain name for the GitLab instance.
gitlab_group : str
    GitLab group name for Franklin exercises.
gitlab_api_url : str
    Full URL for GitLab API endpoint.
gitlab_token : str
    GitLab personal access token for API authentication.
registry_base_url : str
    Base URL for the Docker registry.
github_issues_template_url : str
    Template URL for creating GitHub issues.
conda_channel : str
    Conda channel name for package distribution.
documentation_url : str
    URL template for documentation.
github_write_issue_token : str
    GitHub token for creating issues automatically.
required_gb_free_disk : float
    Minimum required free disk space in gigabytes.
allow_subdirs : bool
    Whether to allow operations in subdirectories.
wrap_width : int
    Character width for text wrapping.
min_window_width : int
    Minimum terminal window width.
min_window_height : int
    Minimum terminal window height.
bold_text_on_windows : bool
    Whether to use bold text on Windows terminals.
pg_options : dict
    Progress bar display options.
pg_ljust : int
    Left justification width for progress bars.
docker_settings : dict
    Default Docker Desktop configuration settings.
"""

from typing import Dict, Any

name: str = 'franklin'
maintainer_email: str = 'kaspermunch@birc.au.dk'

gitlab_domain: str = 'gitlab.au.dk'
gitlab_group: str = 'franklin'
gitlab_api_url: str = f'https://{gitlab_domain}/api/v4'
gitlab_token: str = 'glpat-8F4yGmS6v_xZyqzyyoUM'
registry_base_url: str = f'registry.{gitlab_domain}'
github_issues_template_url: str = 'https://api.github.com/repos/munch-group/{repository_name}/issues'
conda_channel: str = 'munch-group'
documentation_url: str = 'https://munch-group.org/{name}'
github_write_issue_token: str = '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'

required_gb_free_disk: float = 5.0

allow_subdirs: bool = False
wrap_width: int = 75
min_window_width: int = 80
min_window_height: int = 24
bold_text_on_windows: bool = False
pg_options: Dict[str, Any] = dict(fill_char='=', empty_char=' ', width=36, show_eta=False)
pg_ljust: int = 30

docker_settings: Dict[str, Any] = {
            "AutoDownloadUpdates": True,
            "AutoPauseTimedActivitySeconds": 30,
            "AutoPauseTimeoutSeconds": 300,
            "AutoStart": False,
            "Cpus": 5,
            "DisplayedOnboarding": True,
            "EnableIntegrityCheck": True,
            "FilesharingDirectories": [
                "/Users",
                "/Volumes",
                "/private",
                "/tmp",
                "/var/folders"
            ],
            "MemoryMiB": 8000,
            "DiskSizeMiB": 25000,
            "OpenUIOnStartupDisabled": True,
            "ShowAnnouncementNotifications": True,
            "ShowGeneralNotifications": True,
            "SwapMiB": 1024,
            "UseCredentialHelper": True,
            "UseResourceSaver": False,
        }
# container_mem_limit = 2000 # 2 GB
