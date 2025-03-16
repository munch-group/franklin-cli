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

# curl --header "PRIVATE-TOKEN: <myprivatetoken>" -X POST "https://gitlab.com/api/v4/projects?name=myexpectedrepo&namespace_id=38"


# # this will show the namespace details of the Group with ID 54
# curl --header "PRIVATE-TOKEN: ${TOKEN}" "https://gitlab.com/api/v4/namespaces/54

# # this will show the namespace details of the User with username my-username
# curl --header "PRIVATE-TOKEN: ${TOKEN}" "https://gitlab.com/api/v4/namespace/my-username

def get_registry_listing(registry):
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
        # images[(course, exercise)] = entry#['location']
    return images


def get_course_names():
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


def get_exercise_names(course):
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


def pick_course():
    course_names = get_course_names()
    course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
    utils.secho("\nUse arrow keys to select course and press Enter:", fg='green')
    captions = []
    course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
    return course_group_names[course_idx], course_danish_names[course_idx]


def select_exercise(exercises_images):
    while True:
        course, danish_course_name = pick_course()
        exercise_names = get_exercise_names(course)
        # only use those with listed images
        for key in list(exercise_names.keys()):
            if (course, key) not in exercises_images:
                del exercise_names[key]
        if exercise_names:
            break
        utils.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')
        time.sleep(2)

    exercise_repo_names, exercise_danish_names = zip(*sorted(exercise_names.items()))
    utils.secho(f'\nUse arrow keys to select exercise in "{danish_course_name}" and press Enter:', fg='green')
    captions = []
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]

    utils.secho(f"\nSelected:", fg='green')
    utils.echo(f"Course: {danish_course_name}")
    utils.echo(f"Exercise: {exercise_danish_names[exercise_idx]}")
    utils.echo()
    time.sleep(1)

    return course, exercise


def select_image():

    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)

    course, exercise = select_exercise(exercises_images)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


def _config_local_repo(repo_local_path):

    if utils.system() == 'Windows':
        subprocess.check_call(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} config pull.rebase false'))
        subprocess.check_call(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} config merge.tool vscode'))
        subprocess.check_call(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} config mergetool.vscode.cmd "code --wait --merge $REMOTE $LOCAL $BASE $MERGED"'))
        subprocess.check_call(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} config diff.tool vscode'))
        subprocess.check_call(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} config difftool.vscode.cmd "code --wait --diff $LOCAL $REMOTE"'))
    else:
        subprocess.check_call(utils._cmd(f'git -C {repo_local_path} config pull.rebase false'))
        subprocess.check_call(utils._cmd(f"git -C {repo_local_path} config merge.tool vscode"))
        subprocess.check_call(utils._cmd(f"git -C {repo_local_path} config mergetool.vscode.cmd 'code --wait --merge $REMOTE $LOCAL $BASE $MERGED'"))
        subprocess.check_call(utils._cmd(f"git -C {repo_local_path} config diff.tool vscode"))
        subprocess.check_call(utils._cmd(f"git -C {repo_local_path} config difftool.vscode.cmd 'code --wait --diff $LOCAL $REMOTE'"))


def _git_safe_pull(repo_local_path):

    merge_conflict = False
    try:
        # output = subprocess.check_output(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} pull')).decode()
        subprocess.run(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative'), stdout=DEVNULL, stderr=STDOUT, check=True)
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())

        # merge conflict
        output = subprocess.check_output(utils._cmd(f'git -C {PurePosixPath(repo_local_path)} diff --name-only --diff-filter=U --relative')).decode()

        utils.echo('Changes to the following files conflict with changes to the gitlab versions of the same files:')
        utils.echo(output)
        utils.echo("Please resolve any conflicts and then run the command again.")
        utils.echo("For more information on resolving conflicts, see:")
        utils.echo("https://munch-group/franklin/git.html#resolving-conflicts", fg='blue')
        click.pause("Press Enter to launch vscode's mergetool")

        _launch_mergetool(repo_local_path)

        merge_conflict = True

    return merge_conflict


def _merge_in_progress(repo_local_path):
    return os.path.exists(os.path.join(repo_local_path, '.git/MERGE_HEAD'))
    # git merge HEAD


def _launch_mergetool(repo_local_path):
    try:
        output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} mergetool')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())   


def _finish_any_merge_in_progress(repo_local_path):
    if _merge_in_progress(repo_local_path):
        try:
            output = subprocess.check_output(utils._cmd(f'git -C repo_local_path merge --continue --no-edit')).decode()
            utils.secho("Merge continued.", fg='green')
        except subprocess.CalledProcessError as e:
            print(e.output.decode())
            utils.secho("You have merge conflicts. Please resolve the conflicts and then run the command again.", fg='red')
            click.pause("Press Enter to launch vscode's mergetool")
            _launch_mergetool(repo_local_path)
            return


def _gitlab_down():

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
    _finish_any_merge_in_progress(repo_local_path)

    # update or clone the repository
    if os.path.exists(repo_local_path):
        utils.secho(f"The repository '{repo_name}' already exists at {repo_local_path}.")
        if click.confirm('\nDo you want to update the existing repository?', default=True):
            merge_conflict = _git_safe_pull(repo_local_path)
            if merge_conflict:
                return
            else:
                utils.secho(f"Local repository updated.", fg='green')
        else:
            raise click.Abort()
    else:
        try:
            output = subprocess.check_output(utils._cmd(f'git clone {clone_url}')).decode()
        except subprocess.CalledProcessError as e:
            utils.secho(f"Failed to clone repository: {e.output.decode()}", fg='red')
            raise click.Abort()
        utils.secho(f"Local repository updated.", fg='green')

    _config_local_repo(repo_local_path)


def _gitlab_up(repo_local_path, remove_tracked_files):

    if not os.path.exists(repo_local_path):
        utils.secho(f"{repo_local_path} does not exist", fg='red')
        return
    if not os.path.exists(os.path.join(repo_local_path, '.git')):
        utils.secho(f"{repo_local_path} is not a git repository", fg='red')
        return

    _config_local_repo(repo_local_path)

    # Fetch the latest changes from the remote repository
    output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} fetch')).decode()

    # Finish any umcompleted merge
    _finish_any_merge_in_progress(repo_local_path)

    # add
    try:
        output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} add -u')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    try:
        staged_changes = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} diff --cached')).decode()
    except subprocess.CalledProcessError as e:        
        print(e.output.decode())
        raise click.Abort()
    
    if not staged_changes:
        utils.secho("No changes to your local files.", fg='green')
    else:

        # commit
        msg = click.prompt("Enter short description of the nature of the changes", default="an update", show_default=True)
        try:
            output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} commit -m "{msg}"')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()
        
        # pull
        utils.echo("Pulling changes from the remote repository.")
        merge_conflict = _git_safe_pull(repo_local_path)
        if merge_conflict:
            return
        
        # push
        try:
            output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} push')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        utils.secho(f"Changes uploaded to GitLab.", fg='green')

    # # Check the status to see if there are any upstream changes
    # status_output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} status')).decode()
    # if "Your branch is up to date" in status_output:
    #     utils.secho("No changes to upload.", fg='green')
    #     return
    # else:


    if remove_tracked_files:

        try:
            # output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} diff-index --quiet HEAD')).decode()
            output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} status')).decode()
        except subprocess.CalledProcessError as e:        
            print(e.output.decode())
            raise click.Abort()

        if 'nothing to commit, working tree clean' not in output:
            # utils.secho("There are uncommitted changes. Please commit or stash them before removing local files.", fg='red')
            utils.secho("There are local changes to repository files. Local repository will not be removed.", fg='red')
            return
    
        if _merge_in_progress(repo_local_path):
            utils.secho("A merge is in progress. Local repository will not be removed.", fg='red')
            return

        # Instead of deleting the repository dir, we prune all tracked files and 
        # and resulting empty directories - in case there are 
        path = os.path.join(repo_local_path, 'franklin.log')
        if os.path.exists(path):
            os.remove(path)
        output = subprocess.check_output(utils._cmd(f'git -C {repo_local_path} ls-files')).decode()
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

        utils.secho(f"Local files removed.", fg='green')


def _gitlab_status():
    pass

@click.group(cls=utils.AliasedGroup)
def exercise():
    """GitLab commands."""
    pass

@exercise.command('status')
@crash_report
def _status():
    '''Status of local repository'''
    _gitlab_status()

@exercise.command('down')
@crash_report
def gitlab_down():
    '''"Download" exercise from GitLab'''
    _gitlab_down()


@exercise.command('up')
@click.option('-d', '--directory', default=None)
@click.option('--remove/--no-remove', default=True, show_default=True)
@crash_report
def gitlab_up(directory, remove):
    '''"Upload" exercise to GitLab'''
    if directory is None:
        directory = os.getcwd()
    if utils.system() == 'Windows':
        directory = PureWindowsPath(directory)
    _gitlab_up(directory, remove)
