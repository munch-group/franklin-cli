import requests
import time
import click
import subprocess
from subprocess import DEVNULL, STDOUT, PIPE
import os
import sys
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Tuple, List, Dict, Callable, Any
from operator import itemgetter
# import importlib_resources
from . import config as cfg
from . import utils
from . import cutie
from . import terminal as term
from .logger import logger
from .utils import is_educator
from . import system

def get_group_members(group_id: str, api_token: str):
    """Get all members of a group in GitLab."""

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


def get_user_info(user_id: int, api_token: str):
    """Get user information from GitLab by user ID."""
    
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


def get_group_id(group_name, api_token):
    url = f"https://{cfg.gitlab_domain}/api/v4/groups"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers, params={"search": group_name})
    for group in response.json():
        if group["path"] == group_name or group["full_path"] == group_name:
            return group['id']


def get_project_id(project_name, group_id, api_token):
    url = f"https://{cfg.gitlab_domain}/api/v4/groups/{group_id}/projects"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    for project in response.json():
        if project["path"] == project_name or project["name"] == project_name:
            return project['id']


def get_user_id(user_name, api_token):
    url = f"https://{cfg.gitlab_domain}/api/v4/users?username={user_name}"
    headers = {"PRIVATE-TOKEN": api_token}
    response = requests.get(url, headers=headers)
    user = response.json()[0]
    return user['id']


def get_project_visibility(course, exercise, api_token):

    project_path = f'{cfg.gitlab_group}/{course}/{exercise}'
    url = f"{cfg.gitlab_api_url}/projects/{requests.utils.quote(project_path, safe='')}"

    response = requests.get(url, headers = {"PRIVATE-TOKEN": api_token})
    if response.status_code == 200:
        return response.json().get("visibility")
    else:
        print(f"Failed to fetch project info: {response.status_code}")


def create_public_gitlab_project(project_name: str, course: str,
                          api_token: str = None) -> None:

    if gitlab_token is None:
        gitlab_token = cfg.gitlab_token

    headers = {
        "PRIVATE-TOKEN": gitlab_token,
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
    Fetches the listing of images in the GitLab registry.

    Parameters
    ----------
    registry : 
        URl to the GitLab registry.

    Returns
    -------
    :
        A dictionary with the course and exercise names as keys and 
        the image locations
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
    Fetches the names of the courses in the GitLab group.

    Returns
    -------
    :
        A dictionary with the course names and the Danish course names
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
    Fetches the names of the exercises in the GitLab group.

    Parameters
    ----------
    course : 
        Course name.

    Returns
    -------
    :
        A dictionary with the exercise names and the Danish exercise names
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
    Prompts the user to select a course.

    Returns
    -------
    :
        The course name and the Danish name of the course.
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

def pick_exercise(course: str, danish_course_name, exercises_images) -> Tuple[str, str]:

    # hide_hidden = not is_educator()
    is_edu = is_educator()
    while True:
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
            break
        term.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')
        time.sleep(2)

    exercise_repo_names, listed_exercise_names = \
        zip(*sorted(exercise_names.items(), key=itemgetter(1)))
    term.secho(f'\nUse arrow keys to select exercise in '
               f'"{danish_course_name}" and press Enter:', fg='green')
    captions = []
    exercise_idx = cutie.select(listed_exercise_names, 
                                caption_indices=captions, selected_idx=0)
    exercise = exercise_repo_names[exercise_idx]

    return exercise, listed_exercise_names[exercise_idx]


def select_exercise(exercises_images:list=None) -> Tuple[str, str]:
    """
    Prompts the user to select an exercise.

    Parameters
    ----------
    exercises_images : 
        A dictionary with the exercise and exercise names as keys and 
        the image locations

    Returns
    -------
    :
        A tuple of the course name and the exercise name.
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
    Prompts the user to select a course, then an exercise mapping to an 
    image location.

    Returns
    -------
    :
        Image location.
    """
    url = \
        f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    exercises_images = get_registry_listing(url)

    (course, _), (exercise, _) = select_exercise(exercises_images)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


@click.command(epilog=f'See {cfg.documentation_url} for more details')
def download():
    """Download an exercise
    """
    try:
        import franklin_educator

        term.boxed_text("Are you an educator?",
                        ['If you want to edit the version available to students, '
                        'you must use "franklin exercise edit" instead.'],                        
                        fg='blue')
        # term.echo('If you want to edit the version available to students, '
        #           'you must use "franklin exercise edit" instead.')
        click.confirm("Continue?", default=False, abort=True)
    except ImportError:
        pass

    # get images for available exercises
    url = \
        f'{cfg.gitlab_api_url}/groups/{cfg.gitlab_group}/registry/repositories'
    exercises_images = get_registry_listing(url)

    # pick course and exercise
    (course, _), (exercise, listed_exercise_name) = \
        select_exercise(exercises_images)
    listed_exercise_name = listed_exercise_name.replace(' ', '-')

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
    template_dir = Path(os.path.dirname(sys.modules['franklin_educator'].__file__)) / 'data' / 'templates' / 'exercise'
    template_files = list(template_dir.glob('*'))

    dev_files = [p for p in template_files if p != 'exercise.ipynb']

    for path in dev_files:
        path = os.path.join(repo_local_path, path)
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
