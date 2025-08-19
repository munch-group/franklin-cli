import requests
import time
import click
import subprocess
from subprocess import DEVNULL, STDOUT, PIPE
import os
import sys
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Tuple, List, Dict, Callable, Any, Optional, Union
from operator import itemgetter
# import importlib_resources
from . import config as cfg
from . import utils
from . import cutie
from . import terminal as term
from .logger import logger
from .utils import is_educator
from . import system

def get_group_members(group_id: str, api_token: str) -> Dict[int, int]:
    """
    Retrieve all members of a GitLab group with their access levels.

    This function fetches all members (including inherited members) from a
    specified GitLab group and returns their user IDs mapped to access levels.

    Parameters
    ----------
    group_id : str
        The GitLab group ID to fetch members from.
    api_token : str
        GitLab private token with appropriate permissions to read group members.

    Returns
    -------
    Dict[int, int]
        Dictionary mapping user IDs to their access levels in the group.
        Access levels follow GitLab conventions:
        - 10: Guest
        - 20: Reporter
        - 30: Developer
        - 40: Maintainer
        - 50: Owner

    Examples
    --------
    >>> members = get_group_members('123', 'glpat-xxxxx')
    >>> for user_id, access_level in members.items():
    ...     print(f'User {user_id} has access level {access_level}')

    Notes
    -----
    - Uses GitLab API v4 /groups/{id}/members/all endpoint
    - Includes inherited members from parent groups
    - Requires valid API token with group read permissions
    """

    headers = {'PRIVATE-TOKEN': api_token}
    url = f'https://{cfg.gitlab_domain}/api/v4/groups/{group_id}/members/all'

    response = requests.get(url, headers=headers)
    members = {}
    for member in response.json():
        members[member['id']] = member['access_level']
    return members


#def update_project_description(project_id: int, access_token: str, new_description: str):
# # Inputs
# project_id = 123456  # Replace with your project ID
# access_token = 'your_access_token_here'
# new_description = "Updated project description via API."

# # Request
# url = f"https://gitlab.com/api/v4/projects/{project_id}"
# headers = {"PRIVATE-TOKEN": access_token}
# data = {
#     "description": new_description
# }

# response = requests.put(url, headers=headers, data=data)

# # Result
# if response.ok:
#     print("Description updated.")
# else:
#     print(f"Error: {response.status_code}, {response.text}")


# def update_project_permissions(user_id: int, project_id: int, access_level: int, api_token: str):


#     # API endpoint to update existing member
#     url = f"https://{cfg.gitlab_domain}/api/v4/projects/{project_id}/members/{user_id}"

#     headers = {
#         "PRIVATE-TOKEN": api_token,
#         "Content-Type": "application/json"
#     }

#     payload = {
#         "access_level": access_level
#     }

#     # Execute request
#     response = requests.put(url, headers=headers, json=payload)

#     # Output response
#     if response.status_code == 200:
#         print("Access level updated successfully.")
#     elif response.status_code == 404:
#         print("User is not a member of the project.")
#     else:
#         print(f"Error {response.status_code}: {response.json()}")


def get_user_info(user_id: int, api_token: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve detailed user information from GitLab.

    This function fetches comprehensive user information from GitLab including
    username, email, name, and other profile details.

    Parameters
    ----------
    user_id : int
        The GitLab user ID to fetch information for.
    api_token : str
        GitLab private token with appropriate permissions to read user data.

    Returns
    -------
    Optional[Dict[str, Any]]
        Dictionary containing user information if successful, None if user
        not found or access denied. Typical keys include:
        - 'id': User ID
        - 'username': Username
        - 'name': Full name
        - 'email': Email address
        - 'state': Account state (active, blocked, etc.)

    Examples
    --------
    >>> user_info = get_user_info(12345, 'glpat-xxxxx')
    >>> if user_info:
    ...     print(f"User: {user_info['name']} ({user_info['username']})")
    ... else:
    ...     print("User not found")

    Notes
    -----
    - Uses GitLab API v4 /users/{id} endpoint
    - Returns None on error (404, 403, etc.)
    - Prints error message to stdout on failure
    """
    
    # API endpoint to get user information
    # Note: Replace 'your_token' with your actual GitLab private token
    headers = {'PRIVATE-TOKEN': api_token}
    url = f'https://{cfg.gitlab_domain}/api/v4/users/{user_id}'

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching user info: {response.status_code}")
        return None


def get_group_id(group_name: str, api_token: str) -> Optional[int]:
    """
    Find GitLab group ID by group name or path.

    This function searches for a GitLab group by name and returns its ID.
    It matches both the group path and full path.

    Parameters
    ----------
    group_name : str
        The group name or path to search for.
    api_token : str
        GitLab private token with appropriate permissions.

    Returns
    -------
    Optional[int]
        The group ID if found, None if not found.

    Examples
    --------
    >>> group_id = get_group_id('my-group', 'glpat-xxxxx')
    >>> if group_id:
    ...     print(f'Group ID: {group_id}')

    Notes
    -----
    - Uses GitLab API v4 /groups endpoint with search parameter
    - Matches against both 'path' and 'full_path' fields
    - Returns the first matching group's ID
    """
    url = f"https://{cfg.gitlab_domain}/api/v4/groups"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers, params={"search": group_name})
    for group in response.json():
        if group["path"] == group_name or group["full_path"] == group_name:
            return group['id']


def get_project_id(project_name: str, group_id: int, api_token: str) -> Optional[int]:
    """
    Find GitLab project ID within a specific group.

    This function searches for a project within a specified group and
    returns its ID. It matches both project path and name.

    Parameters
    ----------
    project_name : str
        The project name or path to search for.
    group_id : int
        The group ID to search within.
    api_token : str
        GitLab private token with appropriate permissions.

    Returns
    -------
    Optional[int]
        The project ID if found, None if not found.

    Examples
    --------
    >>> project_id = get_project_id('my-project', 123, 'glpat-xxxxx')
    >>> if project_id:
    ...     print(f'Project ID: {project_id}')

    Notes
    -----
    - Uses GitLab API v4 /groups/{id}/projects endpoint
    - Matches against both 'path' and 'name' fields
    - Returns the first matching project's ID
    """
    url = f"https://{cfg.gitlab_domain}/api/v4/groups/{group_id}/projects"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    for project in response.json():
        if project["path"] == project_name or project["name"] == project_name:
            return project['id']


def get_user_id(user_name: str, api_token: str) -> int:
    """
    Find GitLab user ID by username.

    This function searches for a user by username and returns their ID.

    Parameters
    ----------
    user_name : str
        The username to search for.
    api_token : str
        GitLab private token with appropriate permissions.

    Returns
    -------
    int
        The user ID of the first matching user.

    Raises
    ------
    IndexError
        If no user is found with the specified username.

    Examples
    --------
    >>> user_id = get_user_id('john.doe', 'glpat-xxxxx')
    >>> print(f'User ID: {user_id}')

    Notes
    -----
    - Uses GitLab API v4 /users endpoint with username parameter
    - Returns the first matching user's ID
    - Assumes at least one user will be found (may raise IndexError)
    """
    url = f"https://{cfg.gitlab_domain}/api/v4/users?username={user_name}"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    user = response.json()[0]
    return user['id']


def get_project_visibility(course: str, exercise: str, api_token: str) -> Optional[str]:
    """
    Get the visibility setting of a GitLab project.

    This function retrieves the visibility level (public, internal, private)
    of a specific project within the Franklin ecosystem.

    Parameters
    ----------
    course : str
        The course name/identifier.
    exercise : str
        The exercise name/identifier.
    api_token : str
        GitLab private token with appropriate permissions.

    Returns
    -------
    Optional[str]
        The project visibility level ('public', 'internal', 'private')
        if successful, None if project not found or access denied.

    Examples
    --------
    >>> visibility = get_project_visibility('python-101', 'exercise-1', 'glpat-xxxxx')
    >>> print(f'Project visibility: {visibility}')

    Notes
    -----
    - Constructs project path as '{gitlab_group}/{course}/{exercise}'
    - Uses GitLab API v4 /projects/{id} endpoint with URL encoding
    - Prints error message on failure
    """

    project_path = f'{cfg.gitlab_group}/{course}/{exercise}'
    url = f"{cfg.gitlab_api_url}/projects/{requests.utils.quote(project_path, safe='')}"

    response = requests.get(url, headers = {"PRIVATE-TOKEN": api_token})
    if response.status_code == 200:
        return response.json().get("visibility")
    else:
        print(f"Failed to fetch project info: {response.status_code}")


def create_public_gitlab_project(project_name: str, course: str,
                          api_token: Optional[str] = None) -> None:
    """
    Create a new public GitLab project within a course group.

    This function creates a new public GitLab project in the specified
    course subgroup with the given name.

    Parameters
    ----------
    project_name : str
        The name of the project to create.
    course : str
        The course name/identifier where the project should be created.
    api_token : Optional[str], default=None
        GitLab private token. If None, uses the token from configuration.

    Returns
    -------
    None
        This function performs the creation operation and has no return value.

    Examples
    --------
    >>> create_public_gitlab_project('new-exercise', 'python-101')
    >>> create_public_gitlab_project('assignment-1', 'data-science', 'glpat-xxxxx')

    Notes
    -----
    - Creates project with 'public' visibility
    - Places project in the course subgroup namespace
    - Prints success message with project URL or error details
    - Uses configuration gitlab_token if api_token not provided

    Warnings
    --------
    There appears to be a bug in the function where `gitlab_token` is referenced
    but the parameter is named `api_token`.
    """

    if api_token is None:
        api_token = cfg.gitlab_token

    headers = {
        "PRIVATE-TOKEN": api_token,
        "Content-Type": "application/json"
    }
    payload = {
        "name": project_name,
        "visibility": "public",
        "namespace_id": get_group_id(course, api_token),
    }
    response = requests.post(cfg.gitlab_api_url, headers=headers, json=payload)

    # Handle response
    if response.status_code == 201:
        repo_info = response.json()
        print(f"Repository created: {repo_info['web_url']}")
    else:
        print(f"Error {response.status_code}: {response.text}")



def get_registry_listing(registry: str) -> Dict[Tuple[str, str], str]:
    """
    Retrieve available Docker images from GitLab Container Registry.

    This function fetches all available Docker images from the GitLab Container
    Registry and organizes them by course and exercise identifiers.

    Parameters
    ----------
    registry : str
        The URL to the GitLab Container Registry API endpoint.

    Returns
    -------
    Dict[Tuple[str, str], str]
        Dictionary mapping (course, exercise) tuples to image locations.
        Only includes exercise images (excludes 'base' and template images).

    Raises
    ------
    requests.HTTPError
        If the API request fails or returns an error status.

    Examples
    --------
    >>> registry_url = 'https://gitlab.example.com/api/v4/groups/123/registry/repositories'
    >>> images = get_registry_listing(registry_url)
    >>> for (course, exercise), location in images.items():
    ...     print(f'{course}/{exercise}: {location}')

    Notes
    -----
    - Uses authenticated session with GitLab private token
    - Filters out 'base' exercises and template repositories
    - Expects registry entries with path format: 'group/course/exercise'
    - Automatically excludes 'base-images' and 'base-templates' courses
    """
    s = requests.Session()
    s.headers.update({'PRIVATE-TOKEN': cfg.gitlab_token})
    images = {}
    r  = s.get(registry,  headers={ "Content-Type" : "application/json"})
    if not r.ok:
      r.raise_for_status()
    for entry in r.json():
        group, course, exercise = entry['path'].split('/')
        if exercise in ['base']:
            continue
        if course in ['base-images', 'base-templates']:
            continue
        images[(course, exercise)] = entry['location']
    return images


def get_course_names() -> Dict[str, str]:
    """
    Retrieve course names and descriptions from GitLab subgroups.

    This function fetches all course subgroups from the main Franklin GitLab
    group and returns a mapping of internal names to display names.

    Returns
    -------
    Dict[str, str]
        Dictionary mapping course identifiers (paths) to display names
        (descriptions). If a subgroup has no description, the path is
        used as the display name.

    Raises
    ------
    requests.HTTPError
        If the API request fails or returns an error status.

    Examples
    --------
    >>> courses = get_course_names()
    >>> for course_id, display_name in courses.items():
    ...     print(f'{course_id}: {display_name}')

    Notes
    -----
    - Uses authenticated session with GitLab private token from configuration
    - Excludes subgroups with 'template' in the path name
    - Uses subgroup description as display name, falls back to path
    - Accesses GitLab API v4 /groups/{id}/subgroups endpoint
    """
    s = requests.Session()
    s.headers.update({'PRIVATE-TOKEN': cfg.gitlab_token})
    url = f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/subgroups'

    name_mapping = {}
    r  = s.get(url, headers={ "Content-Type" : "application/json"})
    if not r.ok:
        r.raise_for_status()

    for entry in r.json():
        if 'template' in entry['path'].lower():
            continue
        if entry['description']:
            name_mapping[entry['path']] = entry['description']
        else:
            name_mapping[entry['path']] = entry['path']
    
    return name_mapping


def get_exercise_names(course: str) -> Dict[str, str]:
    """
    Retrieve exercise names and descriptions for a specific course.

    This function fetches all projects (exercises) within a course subgroup
    and returns a mapping of internal names to display names.

    Parameters
    ----------
    course : str
        The course identifier to fetch exercises from.

    Returns
    -------
    Dict[str, str]
        Dictionary mapping exercise identifiers (paths) to display names
        (descriptions). If a project has no description, the path is
        used as the display name.

    Raises
    ------
    requests.HTTPError
        If the API request fails or returns an error status.

    Examples
    --------
    >>> exercises = get_exercise_names('python-101')
    >>> for exercise_id, display_name in exercises.items():
    ...     print(f'{exercise_id}: {display_name}')

    Notes
    -----
    - Uses authenticated session with GitLab private token from configuration
    - Only includes non-archived projects
    - Uses project description as display name, falls back to path
    - Accesses GitLab API v4 /groups/{encoded_path}/projects endpoint
    - Course path is URL-encoded for the API request
    """

    s = requests.Session()
    s.headers.update({'PRIVATE-TOKEN': cfg.gitlab_token,
                      "Content-Type" : "application/json"})
    params = {
        "archived": "false",  # must be passed as a string
        # "membership": "true",  # optional: only projects the user is a member of
        # "per_page": 100        # optional: number of results per page
    }
    url = f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}%2F{course}/projects'
    r  = s.get(url, params=params)

    # s = requests.Session()
    # s.headers.update({'PRIVATE-TOKEN': cfg.gitlab_token})
    # url = f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}%2F{course}/projects'
    # r  = s.get(url, headers={ "Content-Type" : "application/json"})
    name_mapping = {}
    if not r.ok:
        r.raise_for_status()

    for entry in r.json():
        if entry['description']:
            name_mapping[entry['path']] = entry['description']
        else:
            name_mapping[entry['path']] = entry['path']

    return name_mapping


def pick_course() -> Tuple[str, str]:
    """
    Interactively prompt user to select a course from available options.

    This function displays a list of available courses and allows the user
    to select one using arrow keys and Enter.

    Returns
    -------
    Tuple[str, str]
        A tuple containing:
        - Course identifier (str): The internal course path/name
        - Display name (str): The human-readable course name/description

    Examples
    --------
    >>> course_id, course_name = pick_course()
    >>> print(f'Selected course: {course_name} (ID: {course_id})')

    Notes
    -----
    - Uses cutie library for interactive terminal selection
    - Courses are sorted alphabetically by display name
    - Default selection is the first course in the list
    - Displays green-colored instruction text
    """
    course_names = get_course_names()
    course_group_names, course_danish_names, = \
        zip(*sorted(course_names.items()))
    term.echo()
    term.secho("Use arrow keys to select course and press Enter:", fg='green')
    captions = []
    course_idx = cutie.select(course_danish_names, 
                              caption_indices=captions, selected_idx=0)
    return course_group_names[course_idx], course_danish_names[course_idx]


def pick_exercise(course: str, danish_course_name: str, exercises_images: Optional[Dict[Tuple[str, str], str]]) -> Tuple[str, str]:
    """
    Interactively prompt user to select an exercise from a course.

    This function displays available exercises for a course, filtering based
    on user role (educator vs student) and Docker image availability.

    Parameters
    ----------
    course : str
        The course identifier to select exercises from.
    danish_course_name : str
        The display name of the course for user messages.
    exercises_images : Optional[Dict[Tuple[str, str], str]]
        Dictionary mapping (course, exercise) tuples to image locations.
        If None, no image filtering is applied.

    Returns
    -------
    Tuple[str, str]
        A tuple containing:
        - Exercise identifier (str): The internal exercise path/name
        - Display name (str): The human-readable exercise name

    Examples
    --------
    >>> exercise_id, exercise_name = pick_exercise(
    ...     'python-101', 'Python Programming', images_dict
    ... )
    >>> print(f'Selected: {exercise_name} (ID: {exercise_id})')

    Notes
    -----
    - Filters exercises based on user role (educator vs student)
    - Students cannot see exercises marked as 'HIDDEN' or without Docker images
    - Educators see all exercises with status annotations
    - Retries if no exercises are available for the course
    - Uses cutie library for interactive terminal selection
    - Exercises are sorted alphabetically by display name
    """

    # hide_hidden = not is_educator()
    is_edu = is_educator()
    # while True:
        
    exercise_names = get_exercise_names(course)
    # only use those with listed images and not with 'HIDDEN' in the name

    for key, val in list(exercise_names.items()):            
        hidden_to_students = 'HIDDEN' in val
        image_required = exercises_images is not None
        has_image = exercises_images and (course, key) in exercises_images

        if is_edu:
            if image_required and not has_image:
                    del exercise_names[key]
            else:
                if hidden_to_students:
                    exercise_names[key] = val + ' (hidden from students)'
                if not has_image:
                    exercise_names[key] = val + ' (no docker image)'
        else:
            # student
            if not has_image or hidden_to_students:
                del exercise_names[key]

    if exercise_names:
        print(exercise_names)
        exercise_repo_names, listed_exercise_names = \
            zip(*sorted(exercise_names.items(), key=itemgetter(1)))
        term.secho(f'\nUse arrow keys to select exercise in '
                f'"{danish_course_name}" and press Enter:', fg='green')
        captions = []
        exercise_idx = cutie.select(listed_exercise_names, 
                                    caption_indices=captions, selected_idx=0)
        exercise = exercise_repo_names[exercise_idx]

        return exercise, listed_exercise_names[exercise_idx]
    else:
        term.secho(f"\n  >>No exercises available for {danish_course_name}<<", fg='red')
        term.echo()
        time.sleep(1)
        raise click.Abort()


def select_exercise(exercises_images: Optional[Dict[Tuple[str, str], str]] = None) -> Tuple[Tuple[str, str], Tuple[str, str]]:
    """
    Interactively select both course and exercise with full information.

    This function provides a complete selection workflow where the user first
    picks a course, then selects an exercise from that course.

    Parameters
    ----------
    exercises_images : Optional[Dict[Tuple[str, str], str]], default=None
        Dictionary mapping (course, exercise) tuples to Docker image locations.
        Used to filter exercises based on Docker image availability.
        If None, no image-based filtering is applied.

    Returns
    -------
    Tuple[Tuple[str, str], Tuple[str, str]]
        A nested tuple containing:
        - Course info: (course_id, course_display_name)
        - Exercise info: (exercise_id, exercise_display_name)

    Examples
    --------
    >>> (course_id, course_name), (exercise_id, exercise_name) = select_exercise()
    >>> print(f'Course: {course_name}')
    >>> print(f'Exercise: {exercise_name}')

    Notes
    -----
    - Combines pick_course() and pick_exercise() functionality
    - Respects user role permissions and image availability
    - Provides complete selection workflow for Franklin exercises
    """
    # # hide_hidden = not is_educator()
    # is_edu = is_educator()
    course, danish_course_name = pick_course()
    exercise, listed_exercise_name = pick_exercise(course, danish_course_name, 
                                                   exercises_images)
    return ((course, danish_course_name), 
            (exercise, listed_exercise_name))

    # while True:
    #     exercise_names = get_exercise_names(course)
    #     # only use those with listed images and not with 'HIDDEN' in the name

    #     for key, val in list(exercise_names.items()):            
    #         hidden_to_students = 'HIDDEN' in val
    #         image_required = exercises_images is not None
    #         has_image = exercises_images and (course, key) in exercises_images

    #         if is_edu:
    #             if image_required and not has_image:
    #                  del exercise_names[key]
    #             else:
    #                 if hidden_to_students:
    #                     exercise_names[key] = val + ' (hidden from students)'
    #                 if not has_image:
    #                     exercise_names[key] = val + ' (no docker image)'
    #         else:
    #             # student
    #             if not has_image or hidden_to_students:
    #                 del exercise_names[key]

    #     if exercise_names:
    #         break
    #     term.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')
    #     time.sleep(2)

    # exercise_repo_names, listed_exercise_names = \
    #     zip(*sorted(exercise_names.items()))
    # term.secho(f'\nUse arrow keys to select exercise in '
    #            f'"{danish_course_name}" and press Enter:', fg='green')
    # captions = []
    # exercise_idx = cutie.select(listed_exercise_names, 
    #                             caption_indices=captions, selected_idx=0)
    # exercise = exercise_repo_names[exercise_idx]

    # # term.secho(f"\nSelected: '{listed_exercise_names[exercise_idx]}'",
    # #            f" in '{danish_course_name}'")
    # # term.echo()
    # # time.sleep(1)

    # return ((course, danish_course_name), 
    #         (exercise, listed_exercise_names[exercise_idx]))


def select_image() -> str:
    """
    Interactively select a Docker image by choosing course and exercise.

    This function provides a complete workflow for selecting a Docker image:
    1. Fetches available images from GitLab Container Registry
    2. Prompts user to select course and exercise
    3. Returns the corresponding Docker image location

    Returns
    -------
    str
        The Docker image location/URL for the selected exercise.

    Examples
    --------
    >>> image_url = select_image()
    >>> print(f'Selected image: {image_url}')

    Notes
    -----
    - Only shows exercises that have associated Docker images
    - Uses GitLab Container Registry API to fetch available images
    - Combines registry listing with interactive selection
    - Returns the full image location suitable for Docker operations
    """
    url = \
        f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    exercises_images = get_registry_listing(url)

    (course, _), (exercise, _) = select_exercise(exercises_images)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


@click.option('--vscode', default=False, is_flag=True,
              help='Include vscode devcontainer files in the download.')
@click.command(epilog=f'See {cfg.documentation_url} for more details')
def download(vscode: bool) -> None:
    """
    Download a Franklin exercise repository to the local filesystem.

    This command provides an interactive interface for selecting and downloading
    exercise repositories from GitLab. It clones the repository and prepares
    it for student use by removing development files.

    Returns
    -------
    None
        This command performs file operations and has no return value.

    Raises
    ------
    click.Abort
        If the target directory already exists or user cancels operation.

    Examples
    --------
    Run interactively:
    >>> franklin download

    Notes
    -----
    - Warns educators to use 'franklin exercise edit' instead for editing
    - Only shows exercises with available Docker images
    - Clones repository to current directory with exercise name
    - Removes development files (keeping only exercise.ipynb)
    - Creates a clean student environment
    - Checks for existing directories to prevent conflicts
    """
    # Check if educator plugin is installed without importing it
    try:
        from importlib.metadata import entry_points
        educator_plugins = entry_points().select(group='franklin.plugins', name='exercise')
        if educator_plugins:
            # Educator plugin is installed
            term.boxed_text("Are you an educator?",
                            ['If you want to edit the version available to students, '
                            'you must use "franklin exercise edit" instead.'],                        
                            fg='blue')
            click.confirm("Continue?", default=False, abort=True)
    except Exception:
        pass

    # get images for available exercises
    url = \
        f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    exercises_images = get_registry_listing(url)

    # pick course and exercise
    (course, _), (exercise, listed_exercise_name) = \
        select_exercise(exercises_images)
    listed_exercise_name = listed_exercise_name.replace(' ', '-').replace(':', '')

    # url for cloning the repository
    repo_name = exercise.split('/')[-1]
    clone_url = \
        f'https://gitlab.au.dk/{cfg.gitlab_group}/{course}/{repo_name}.git'
    repo_local_path = Path().cwd() / listed_exercise_name

    # if system.system() == 'Windows':
    #     repo_local_path = PureWindowsPath(repo_local_path)

    if repo_local_path.exists():
        term.secho(f"The exercise folder already exists:\n{repo_local_path.absolute()}.")
        raise click.Abort()

    output = utils.run_cmd(f'git clone {clone_url} "{repo_local_path}"')

    # iterdir = (importlib_resources
    #            .files()
    #            .joinpath('data/templates/exercise')
    #            .iterdir()
    # )
    # template_files = [p.name for p in iterdir]
    # Use template from franklin core package instead of franklin_educator
    template_dir = Path(os.path.dirname(__file__)) / 'data' / 'templates' / 'exercise'
    template_files = list(template_dir.glob('*'))

    if vscode:
        include_files = [p for p in template_files if p.name not in ['exercise.ipynb', '.devcontainer', 'Dockerfile']]
    else:
        include_files = [p for p in template_files if p.name not in ['exercise.ipynb']]
    dev_files = [p for p in template_files if p.name not in include_files]

    for template_path in dev_files:
        path = os.path.join(repo_local_path, template_path.name)
        if os.path.exists(path):
            logger.debug(f"Removing {path}")
            if os.path.isdir(path):
                import stat
                def on_rm_error(func, path, exc_info):
                    os.chmod(path, stat.S_IWRITE) # make writable and retry
                    func(path)
                utils.rmtree(path)
            else:
                os.remove(path)

    term.secho(f"Downloaded exercise to folder: {repo_local_path}")
