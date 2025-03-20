import requests
from .config import GITLAB_API_URL, GITLAB_GROUP, GITLAB_TOKEN
from . import utils
from . import cutie
import time
import click
from .utils import crash_report
import subprocess
from subprocess import DEVNULL, STDOUT, PIPE
import os
import shutil
from pathlib import Path, PurePosixPath, PureWindowsPath
from . import terminal as term
from typing import Tuple, List, Dict, Callable, Any

# curl --header "PRIVATE-TOKEN: <myprivatetoken>" -X POST "https://gitlab.com/api/v4/projects?name=myexpectedrepo&namespace_id=38"


# # this will show the namespace details of the Group with ID 54
# curl --header "PRIVATE-TOKEN: ${TOKEN}" "https://gitlab.com/api/v4/namespaces/54

# # this will show the namespace details of the User with username my-username
# curl --header "PRIVATE-TOKEN: ${TOKEN}" "https://gitlab.com/api/v4/namespace/my-username

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
        A dictionary with the course and exercise names as keys and the image locations
    """
    s = requests.Session()
    # s.auth = ('user', 'pass')
    s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
    # s.headers.update({'PRIVATE-TOKEN': 'glpat-BmHo-Fh5R\_TvsTHqojzz'})
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
    s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
    url = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/subgroups'

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
    s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
    url = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}%2F{course}/projects'

    name_mapping = {}
    r  = s.get(url, headers={ "Content-Type" : "application/json"})
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
    course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
    term.secho("\nUse arrow keys to select course and press Enter:", fg='green')
    captions = []
    course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
    return course_group_names[course_idx], course_danish_names[course_idx]


def select_exercise(exercises_images: str) -> Tuple[str, str]:
    """
    Prompts the user to select an exercise.

    Parameters
    ----------
    exercises_images : 
        A dictionary with the exercise and exercise names as keys and the image locations

    Returns
    -------
    :
        A tuple of the course name and the exercise name.
    """
    while True:
        course, danish_course_name = pick_course()
        exercise_names = get_exercise_names(course)
        # only use those with listed images
        for key in list(exercise_names.keys()):
            if (course, key) not in exercises_images:
                del exercise_names[key]
        if exercise_names:
            break
        term.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')
        time.sleep(2)

    exercise_repo_names, exercise_danish_names = zip(*sorted(exercise_names.items()))
    term.secho(f'\nUse arrow keys to select exercise in "{danish_course_name}" and press Enter:', fg='green')
    captions = []
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]

    term.secho(f"\nSelected:", fg='green')
    term.echo(f"Course: {danish_course_name}")
    term.echo(f"Exercise: {exercise_danish_names[exercise_idx]}")
    term.echo()
    time.sleep(1)

    return course, exercise


def select_image() -> str:
    """
    Prompts the user to select a course, then an exercise mapping to an image location.

    Returns
    -------
    :
        Image location.
    """

    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)

    course, exercise = select_exercise(exercises_images)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


def config_local_repo(repo_local_path: str) -> None:
    """
    Configures the local repository with the necessary settings for using vscode as the merge and diff tool.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.
    """

    if utils.system() == 'Windows':
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config pull.rebase false'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config merge.tool vscode'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config mergetool.vscode.cmd "code --wait --merge $REMOTE $LOCAL $BASE $MERGED"'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config diff.tool vscode'))
        subprocess.check_call(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} config difftool.vscode.cmd "code --wait --diff $LOCAL $REMOTE"'))
    else:
        subprocess.check_call(utils.fmt_cmd(f'git -C {repo_local_path} config pull.rebase false'))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config merge.tool vscode"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config diff.tool vscode"))
        subprocess.check_call(utils.fmt_cmd(f"git -C {repo_local_path} config difftool.vscode.cmd 'code --wait --diff $LOCAL $REMOTE'"))

    # if utils.system() == 'Windows':
    #     path = os.path.join(os.getenv('APPDATA'), 'gitui')
    # else:
    #     path = str(Path.home() / '.config/gitui')
    # if not os.path.exists(path):
    #     os.makedirs(path)       
    # for file in ['key_bindings.ron', 'key_symbols.toml', 'theme.ron']:     
    #     shutil.copy(file, path)

def git_safe_pull(repo_local_path: str) -> bool:
    """
    Pulls changes from the remote repository and checks for merge conflicts.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.

    Returns
    -------
    :
        True if there is a merge conflict, False otherwise.
    """

    merge_conflict = False
    try:
        # output = subprocess.check_output(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} pull')).decode()
        subprocess.run(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative'), stdout=DEVNULL, stderr=STDOUT, check=True)
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())

        # merge conflict
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative')).decode()

        term.echo('Changes to the following files conflict with changes to the gitlab versions of the same files:')
        term.echo(output)
        term.echo("Please resolve any conflicts and then run the command again.")
        term.echo("For more information on resolving conflicts, see:")
        term.echo("https://munch-group/franklin/git.html#resolving-conflicts", fg='blue')
        click.pause("Press Enter to launch vscode's mergetool")

        launch_mergetool(repo_local_path)

        merge_conflict = True

    return merge_conflict


def merge_in_progress(repo_local_path: str) -> bool:
    """
    Checks if a merge is in progress.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.

    Returns
    -------
    :
        True if a merge is in progress, False otherwise.
    """
    return os.path.exists(os.path.join(repo_local_path, '.git/MERGE_HEAD'))
    # git merge HEAD


def launch_mergetool(repo_local_path: str) -> None:
    """
    Launches vscode's mergetool.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository
    """
    try:
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} mergetool')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())   


def finish_any_merge_in_progress(repo_local_path):
    if merge_in_progress(repo_local_path):
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C repo_local_path merge --continue --no-edit')).decode()
            term.secho("Merge continued.", fg='green')
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            term.secho("You have merge conflicts. Please resolve the conflicts and then run the command again.", fg='red')
            click.pause("Press Enter to launch vscode's mergetool")
            launch_mergetool(repo_local_path)
            return


def git_down() -> None:
    """
    "Downloads" an exercise from GitLab.
    """

    # get images for available exercises
    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)

    # pick course and exercise
    course, exercise = select_exercise(exercises_images)

    # url for cloning the repository
    repo_name = exercise.split('/')[-1]
    clone_url = f'git@gitlab.au.dk:{GITLAB_GROUP}/{course}/{repo_name}.git'
    repo_local_path = os.path.join(os.getcwd(), repo_name)
    if utils.system() == 'Windows':
        repo_local_path = PureWindowsPath(repo_local_path)

    # check if we are in an already cloned repo
    os.path.dirname(os.path.realpath(__file__))
    if os.path.basename(os.getcwd()) == repo_name and os.path.exists('.git'):
        repo_local_path = os.path.join(os.getcwd())

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

    # update or clone the repository
    if os.path.exists(repo_local_path):
        term.secho(f"The repository '{repo_name}' already exists at {repo_local_path}.")
        if click.confirm('\nDo you want to update the existing repository?', default=True):
            merge_conflict = git_safe_pull(repo_local_path)
            if merge_conflict:
                return
            else:
                term.secho(f"Local repository updated.", fg='green')
        else:
            raise click.Abort()
    else:
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git clone {clone_url}')).decode()
        except subprocess.CalledProcessError as e:
            term.secho(f"Failed to clone repository: {e.output.decode()}", fg='red')
            raise click.Abort()
        term.secho(f"Local repository updated.", fg='green')

    config_local_repo(repo_local_path)


def git_up(repo_local_path: str, remove_tracked_files: bool) -> None:
    """
    "Uploads" an exercise to GitLab.

    Parameters
    ----------
    repo_local_path : 
        Path to the local repository.
    remove_tracked_files : 
        Whether to remove the tracked files after uploading
    """

    if not os.path.exists(repo_local_path):
        term.secho(f"{repo_local_path} does not exist", fg='red')
        return
    if not os.path.exists(os.path.join(repo_local_path, '.git')):
        term.secho(f"{repo_local_path} is not a git repository", fg='red')
        return

    config_local_repo(repo_local_path)

    # Fetch the latest changes from the remote repository
    output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} fetch')).decode()

    # Finish any umcompleted merge
    finish_any_merge_in_progress(repo_local_path)

    # add
    try:
        output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} add -u')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    try:
        staged_changes = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} diff --cached')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    if not staged_changes:
        term.secho("No changes to your local files.", fg='green')
    else:

        # commit
        msg = click.prompt("Enter short description of the nature of the changes", default="an update", show_default=True)
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} commit -m "{msg}"')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()
        
        # pull
        term.echo("Pulling changes from the remote repository.")
        merge_conflict = git_safe_pull(repo_local_path)
        if merge_conflict:
            return
        
        # push
        try:
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} push')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        term.secho(f"Changes uploaded to GitLab.", fg='green')

    # # Check the status to see if there are any upstream changes
    # status_output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} status')).decode()
    # if "Your branch is up to date" in status_output:
    #     term.secho("No changes to upload.", fg='green')
    #     return
    # else:


    if remove_tracked_files:

        try:
            # output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} diff-index --quiet HEAD')).decode()
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} status')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        if 'nothing to commit, working tree clean' in output:
            shutil.rmtree(repo_local_path)
            term.secho("Local repository removed.", fg='green')


        elif 'nothing added to commit but untracked files present' in output:

            if merge_in_progress(repo_local_path):
                term.secho("A merge is in progress. Local repository will not be removed.", fg='red')
                return

            # Instead of deleting the repository dir, we prune all tracked files and 
            # and resulting empty directories - in case there are 
            path = os.path.join(repo_local_path, 'franklin.log')
            if os.path.exists(path):
                os.remove(path)
            output = subprocess.check_output(utils.fmt_cmd(f'git -C {repo_local_path} ls-files')).decode()
            tracked_dirs = set()
            for line in output.splitlines():
                path = os.path.join(repo_local_path, *(line.split('/')))
                tracked_dirs.add(os.path.dirname(path))
                os.remove(path)
            # traverse repo bottom up and remove empty directories
            subdirs = reversed([x[0] for x in os.walk(repo_local_path) if os.path.isdir(x[0])])
            for subdir in subdirs:
                if not os.listdir(subdir) and subdir in tracked_dirs:
                    os.rmdir(subdir)
            path = os.path.join(repo_local_path, '.git')
            if os.path.exists(path):
                shutil.rmtree(path)
            if os.path.exists(repo_local_path) and not os.listdir(repo_local_path):
                os.rmdir(repo_local_path)

            term.secho(f"Local files removed.", fg='green')

        else:
            # term.secho("There are uncommitted changes. Please commit or stash them before removing local files.", fg='red')
            term.secho("There are local changes to repository files. Local repository will not be removed.", fg='red')
            return
    

def git_status() -> None:
    """Displays the status of the local repository.
    """
    pass

@click.group(cls=utils.AliasedGroup)
def git():
    """GitLab commands.
    """
    pass

@git.command()
@crash_report
def status():
    """Status of local repository.
    """
    git_status()

@git.command()
@crash_report
def down():
    """Safely git clone or pull from the remote repository.
    
    Convenience function for adding, committing, and pushing changes to the remote repository.    
    """
    git_down()


@git.command()
@click.option('-d', '--directory', default=None)
@click.option('--remove/--no-remove', default=True, show_default=True)
@crash_report
def up(directory, remove):
    """Safely add, commit, push and remove if possible.
    """
    if directory is None:
        directory = os.getcwd()
    if utils.system() == 'Windows':
        directory = PureWindowsPath(directory)
    git_up(directory, remove)

@git.command()
@crash_report
def ui():
    """GitUI for interactive git
    
    Git UI for interactive staging, committing and pushing changes to the remote repository.
    """
    subprocess.run(utils.fmt_cmd(f'gitui'), check=False)



###########################################################
# Group alias "exercise" the status, down and up  commands 
# So users can do franklin exercise down / up / status
###########################################################

@click.group(cls=utils.AliasedGroup)
def exercise():
    """GitLab commands.
    """
    pass

@exercise.command()
@crash_report
def status():
    """Status of local repository.
    """
    git_status()

@exercise.command()
@crash_report
def down():
    """Get local copy of exercise from GitLab
    """
    git_down()


@exercise.command()
@click.option('-d', '--directory', default=None)
@click.option('--remove/--no-remove', default=True, show_default=True)
@crash_report
def up(directory, remove):
    """Sync local copy or exercise to GitLab
    """
    if directory is None:
        directory = os.getcwd()
    if utils.system() == 'Windows':
        directory = PureWindowsPath(directory)
    git_up(directory, remove)
