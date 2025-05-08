

maintainer_email = 'kaspermunch@birc.au.dk'
conda_channel = 'munch-group'
gitlab_domain = 'gitlab.au.dk'
registry_base_url = 'registry.gitlab.au.dk'
gitlab_group = 'franklin'
gitlab_api_url = 'https://gitlab.au.dk/api/v4'
# gitlab_token = 'glpat-tiYpz3zJ95qzVXnyN8--'
# gitlab_token = 'glpat-vxYEphvsCBSzvgGUM8Yf'
gitlab_token = 'glpat-8F4yGmS6v_xZyqzyyoUM'
required_gb_free_disk = 5.0
allow_subdirs = False
wrap_width = 75
min_window_width = 80
min_window_height = 24
bold_text_on_windows = False
pg_options = dict(fill_char='=', empty_char=' ', width=36, show_eta=False)
pg_ljust = 30
docker_settings = {
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
