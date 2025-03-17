

MAINTAINER_EMAIL = 'kaspermunch@birc.au.dk'
ANACONDA_CHANNEL = 'munch-group'
REGISTRY_BASE_URL = 'registry.gitlab.au.dk'
GITLAB_GROUP = 'franklin'
# GITLAB_GROUP = 'mbg-exercises'
GITLAB_API_URL = 'https://gitlab.au.dk/api/v4'
GITLAB_TOKEN = 'glpat-tiYpz3zJ95qzVXnyN8--'
REQUIRED_GB_FREE_DISK = 5.0
ALLOW_SUBDIRS = False
WRAP_WIDTH = 75
MIN_WINDOW_WIDTH = 80
MIN_WINDOW_HEIGHT = 24
BOLD_TEXT_ON_WINDOWS = False
PG_OPTIONS = dict(fill_char='=', empty_char=' ', width=36, show_eta=False)
DOCKER_SETTINGS = {
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
CONTAINER_MEMORY_LIMIT = 2000 # 2 GB
