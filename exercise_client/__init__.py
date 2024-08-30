import platform
from collections import defaultdict
import shlex
import shutil
import subprocess
from subprocess import Popen, PIPE, STDOUT, DEVNULL, CalledProcessError
if platform.system() == "Windows":
    from subprocess import DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP
import sys
import os
# from distutils.version import LooseVersion
# from packaging.version import Version
import requests
import asyncio
import time
import webbrowser
import re
from os.path import expanduser
import json
import signal
import argparse
from textwrap import wrap

import shutil

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(filename='exercise.log', level=logging.DEBUG)
# logging.basicConfig(level=logging.INFO)

from . import cutie

MAINTAINER_EMAIL = 'kaspermunch@birc.au.dk'
ANACONDA_CHANNEL = 'kaspermunch'
REGISTRY_BASE_URL = 'registry.gitlab.au.dk'
GITLAB_GROUP = 'mbg-exercises'
GITLAB_API_URL = 'https://gitlab.au.dk/api/v4'
GITLAB_TOKEN = 'glpat-tiYpz3zJ95qzVXnyN8--'

class CleanupAndTerminate(Exception):
    pass

class DelayedKeyboardInterrupt:
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)
                
    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        # logging.debug('SIGINT received. Delaying KeyboardInterrupt.')
    
    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received:
            self.old_handler(*self.signal_received)

class SuppressedKeyboardInterrupt:
    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)
                
    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        # logging.debug('SIGINT received. Delaying KeyboardInterrupt.')
    
    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)

def format_cmd(cmd):
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0]) 
    return cmd

# def newer_version_of_package():
#     cmd = f'conda search -c {ANACONDA_CHANNEL} exercise-client'

#     p = Popen(format_cmd(cmd), stdout=PIPE, stderr=DEVNULL, text=True)
#     conda_search, _ = p.communicate()
#     newest_version = conda_search.strip().splitlines()[-1].split()[1]

#     cmd = 'conda list -f exercise-client'
#     p = Popen(format_cmd(cmd), stdout=PIPE, stderr=DEVNULL, text=True)
#     conda_search, _ = p.communicate()
#     this_version = conda_search.strip().splitlines()[-1].split()[1]

#     if Version(newest_version) > Version(this_version):
#         return newest_version


def docker_installed():
    if platform.system() == 'Darwin':
        return shutil.which('docker')
    if platform.system() == 'Linux':
        return shutil.which('docker')
    if platform.system() == 'Windows':
        return shutil.which('docker')
    return False


def select_image(exercises_images):

    # print(exercise_list)
    # image_tree = defaultdict(lambda: defaultdict(str))
    # for course, exercise in exercise_dict:
    #     # c, w, v = image_name.split('-')
    #     # image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name
    #     image_tree[course][exercise] = image_name

    print("\nSelect course, week, and exercise below (use arrow keys to move, enter to select)")

    def pick_course():
        course_names = get_course_names()
        course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
        print("\nSelect course:")
        captions = []
        # options = list(image_tree.keys())
        # course = options[cutie.select(options, caption_indices=captions, selected_index=0)]
        course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
        return course_group_names[course_idx], course_danish_names[course_idx]

    while True:
        course, danish_course_name = pick_course()

        exercise_names = get_exercise_names(course)

        # only use those with listed images
        for key in list(exercise_names.keys()):
            if (course, key) not in exercises_images:
                del exercise_names[key]

        if exercise_names:
            break

        print(f"\n  >>No exercises for {danish_course_name}<<")

    exercise_repo_names, exercise_danish_names = zip(*sorted(exercise_names.items()))
    print(f"\nSelect exercise in {danish_course_name}:")
    captions = []
    # options = list(image_tree[course].keys())
    # week = options[cutie.select(options, caption_indices=captions, selected_index=0)]
    exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
    exercise = exercise_repo_names[exercise_idx]
    # print("\nSelect exercise:")
    # captions = []
    # options = list(image_tree[course][week].keys())
    # exercise = options[cutie.select(options, caption_indices=captions, selected_index=0)]

    print(f"\nStarting JupyterLab that will work with:\n\n    {danish_course_name}: {exercise_danish_names[exercise_idx]} \n")
    time.sleep(1)

    selected_image = exercises_images[(course, exercise)]
    return selected_image


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
        images[(course, exercise)] = entry['location']
        # images[(course, exercise)] = entry#['location']
    return images


def get_course_names():
    s = requests.Session()
    s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
    url = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/subgroups'
#https://gitlab.au.dk/api/v4/groups/mbg-exercises/subgroups

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


def docker_command(command, silent=False, return_json=False):
    if silent:
        return subprocess.run(format_cmd(command), check=False, stdout=DEVNULL, stderr=DEVNULL)
    if return_json:
        result = []
        for line in subprocess.check_output(format_cmd(command + ' --format json')).decode().strip().splitlines():
            result.append(json.loads(line))
        return result
    else:
        return subprocess.check_output(format_cmd(command)).decode().strip()


def docker_volume_ls():
    return docker_command('docker volume ls', return_json=True)


def docker_images():
    return docker_command('docker images', return_json=True)


def docker_pull(image_url):
    print("Downloading resources (this can take 10 min or more) ... ", end='', flush=True)
    # return os.system(f'docker pull {image_url}:main')
    docker_command(f'docker pull {image_url}:main', silent=True)
    print("done.", flush=True)


def docker_containers():
    return docker_command('docker ps', return_json=True)


def docker_prune_containers():
    docker_command(f'docker container prune --filter="Name={REGISTRY_BASE_URL}*"', silent=True)


def docker_prune_volumes():
    docker_command(f'docker volume --filter="Name={REGISTRY_BASE_URL}*"')


def docker_prune_all():
    docker_command(f'docker prune -a', silent=True)


def docker_rm_image(image, force=False):
    if force:
        docker_command(f'docker image rm -f {image}', silent=True)
    else:
        docker_command(f'docker image rm {image}', silent=True)


def docker_kill(container_id):
    docker_command(f'docker kill {container_id}', silent=True)


def docker_cleanup():
    for image in docker_images():
        if image['Repository'].startswith(REGISTRY_BASE_URL):
            docker_rm_image(image['ID'])
    docker_prune_containers()
    docker_prune_volumes()
    docker_prune_all()


def docker_image_exists(image_url):
    for image in docker_images():
        if image['Repository'].startswith(image_url):
            return True
    return False


def above_subdir_limit(allowed_depth):
    for dir, _, _ in os.walk('.'):
        if len(dir.split('/')) > allowed_depth:
            return True
    return False


def wrap_text(text):
    return "\n".join(wrap(' '.join(text.split()), 80))    

# async def ainput(string: str) -> str:
#     await asyncio.get_event_loop().run_in_executor(
#             None, lambda s=string: sys.stdout.write(s+' '))
#     return await asyncio.get_event_loop().run_in_executor(
#             None, sys.stdin.readline)

# line = await .ainput('Is this your line? ')

# docker_run_p = None

# @atexit.register
# def kill_child():
#     logging.debug('atexit handler called')
#     if docker_run_p is None:
#         pass
#     else:
#         os.kill(docker_run_p, signal.SIGTERM)
#         docker_run_p.kill()
#         docker_run_p.wait()


def launch_exercise():

    description = """
    Bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla
    bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla.
    """

    not_wrapped = """Bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla bla."""

    description = wrap_text(description) + "\n\n" + not_wrapped

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                        description="description")

    parser.add_argument("-v", "--verbose",
                    dest="verbose",
                    action='store_true',
                    help="Print debugging information")
    parser.add_argument("-f", "--fixme",
                    dest="fixme",
                    action='store_true',
                    help="Run trouble shooting")
    parser.add_argument("-c", "--clone",
                    dest="clone",
                    action='store_true',
                    help="Also clone the repository")
    parser.add_argument("-a", "--at-your-own-risk",
                    dest="at_your_own_risk",
                    action='store_true',
                    help="Override check for maximum depths of mounted directories")
    parser.add_argument("-s", "--skip-update-check",
                    dest="skip_update_check",
                    action='store_true',
                    help="Override check for package updates")

    # cleanup docker images and containers when terminal window is closed
    cleanup = False

    args = parser.parse_args()

    if args.fixme:
        # run trouble shooting
        pass

    # gb_free = shutil.disk_usage('/').free / 1024**3
    # if gb_free < 10:


    if args.skip_update_check:
        logger.debug('Update check skipped')
    else:
        print('Updating package...', end='', flush=True)
        # cmd = f"{os.environ['CONDA_EXE']} update -y -c {ANACONDA_CHANNEL} --no-update-deps exercise-client"
        cmd = f"conda update -y -c {ANACONDA_CHANNEL} --no-update-deps exercise-client"
        logger.debug(cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        if stdout:
            [logger.debug(x) for x in stdout.decode().splitlines()]
        if stderr:
            [logger.debug(x) for x in stderr.decode().splitlines()]
        if p.returncode:
            logger.debug(f"Update failed with return code {p.returncode}")
            msg = f"""
            Could not update package. Please try again later.
            If problem persists, please email {MAINTAINER_EMAIL}
            with a screenshot of the error message.
            """
            print(wrap_text(msg))
            sys.exit()
        print('done.', flush=True)
        # newer_version = newer_version_of_package()
        # newer_version = newer_version.replace('*', '') # remove trailing glob
        # if newer_version:
        #     print(f'Package needs to update.')
        #     cmd = f"conda install -y -q -c {ANACONDA_CHANNEL} exercise-client={newer_version}"
        #     print(cmd)
        #     os.system(cmd)
        #     print("\nmbg-exercises updated and ready for use.\n")
        # sys.exit()

    # user home directory and parent working directory
    home = expanduser("~")
    pwd = os.getcwd()

    subdir_limit = 1
    if not args.at_your_own_risk:
        if above_subdir_limit(subdir_limit):
            msg = f"""Please run the command in a directory without any sub-directories"""
            print(wrap_text(msg))
            sys.exit(1)



    if not docker_installed():
        print('Docker is not installed')
        sys.exit(1) 

    # get registry listing
    registry = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/registry/repositories'
    exercises_images = get_registry_listing(registry)
    # image_info = get_registry_listing(registry)
    # exercises_images = dict((key, val['location']) for key, val in image_info.items())

    # select image using menu prompt
    image_url = select_image(exercises_images)

    # image_size = [val['size'] for val in image_info.values() if val['location'] == image_url][0]

    try:
        cmd = 'docker --version'
        p = subprocess.run(format_cmd(cmd), check=True, stdout=DEVNULL, stderr=DEVNULL)
    except CalledProcessError:
        try:
            cmd = r'"C:\Program Files\Docker\Docker\Docker Desktop.exe"'
            p = subprocess.run(cmd, check=True)
            time.sleep(5)
        except CalledProcessError:
            print('\n\nIT SEEMS "DOCKER DESKTOP" IS NOT INSTALLED. PLEASE INSTALL VIA WEBPAGE.\n\n')
            time.sleep(2)
            if platform.system == "Windows":
                webbrowser.open("https://docs.docker.com/desktop/install/windows-install/", new=1)
            if platform.system == "Mac":
                webbrowser.open("https://docs.docker.com/desktop/install/mac-install/", new=1)
            if platform.system == "Linux":
                webbrowser.open("https://docs.docker.com/desktop/install/linux-install/", new=1)
            sys.exit()

    # get local images
    # local_images = docker_images()

    # pull image if not already present
    if not docker_image_exists(image_url):
        docker_pull(image_url)
        assert docker_image_exists(image_url)
        
    # replace backslashes with forward slashes and C: with /c for windows
    if platform.system() == 'Windows':
        pwd = pwd.replace('\\', '/').replace('C:', '/c')
        home = home.replace('\\', '/').replace('C:', '/c')  

    # command for running jupyter docker container
    # cmd = f"docker run --rm --mount type=bind,source={home}/.ssh,target=/tmp/.ssh --mount type=bind,source={home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main"
    cmd = f"docker run --rm --mount type=bind,source={home}/.ssh,target=/tmp/.ssh --mount type=bind,source={home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -p 8888:8888 {image_url}:main"

    # if platform.system() == "Windows":
    #     popen_kwargs = dict(creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    # else:
    #     popen_kwargs = dict(start_new_session = True)
    popen_kwargs = dict()

    # run docker container
    # global docker_run_p
    docker_run_p = Popen(shlex.split(cmd), stdout=DEVNULL, stderr=DEVNULL, **popen_kwargs)

    time.sleep(5)

    # get id of running container
    for cont in docker_containers():
        if cont['Image'].startswith(image_url):
            run_container_id  = cont['ID']
            break
    else:
        print('No running container with image')
        sys.exit()   

    cmd = f"docker logs --follow {run_container_id}"
    docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, bufsize=1, universal_newlines=True, **popen_kwargs)

    # docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, universal_newlines=False, **popen_kwargs)
    # docker_p_nice_stdout = open(os.dup(docker_log_p.stdout.fileno()), newline='') 

    # docker_log_p = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT, **popen_kwargs)
    # docker_p_nice_stdout = open(os.dup(docker_log_p.stdout.fileno()), 'rb') 
    # https://koldfront.dk/making_subprocesspopen_in_python_3_play_nice_with_elaborate_output_1594

# newline determines how to parse newline characters from the stream. It can be None, '', '\n', '\r', and '\r\n'. It works as follows:
# When reading input from the stream, if newline is None, universal newlines mode is enabled. Lines in the input can end in '\n', '\r', or '\r\n', and these are translated into '\n' before being returned to the caller. If it is '', universal newlines mode is enabled, but line endings are returned to the caller untranslated. If it has any of the other legal values, input lines are only terminated by the given string, and the line ending is returned to the caller untranslated.
# When writing output to the stream, if newline is None, any '\n' characters written are translated to the system default line separator, os.linesep. If newline is '' or '\n', no translation takes place. If newline is any of the other legal values, any '\n' characters written are translated to the given string.

#     # signal handler for cleanup when terminal window is closed
#     def handler(signal_nr, frame):
#         with SuppressedKeyboardInterrupt():
#             signal_name = signal.Signals(signal_nr).name
#             logging.debug(f'Signal handler called with signal {signal_name} ({signal_nr})')
            
#             logging.debug('killing docker container')
#             docker_kill(run_container_id)

#             logging.debug('killing docker log process')
#             docker_log_p.kill()

#             logging.debug('waiting for docker log process')
#             docker_log_p.wait()

#             logging.debug('killing docker run process')
#             docker_run_p.kill()
#             #docker_run_p.kill(signal.CTRL_C_EVENT)

#             logging.debug('waiting for docker run process')
#             docker_run_p.wait()

#             if cleanup:
#                 docker_cleanup()
#         sys.exit()
#         #raise Exception

# #os.kill(self.p.pid, signal.CTRL_C_EVENT)

#     # register handler for signals
#     signal.signal(signal.SIGTERM, handler)
#     # signal.signal(signal.SIGINT, handler)
#     signal.signal(signal.SIGABRT, handler)
#     if platform.system() == 'Mac':
#         signal.signal(signal.SIGHUP, handler)
#     if platform.system() == 'Linux':
#         signal.signal(signal.SIGHUP, handler)
#     if platform.system() == 'Windows':
#         signal.signal(signal.SIGBREAK, handler)
#         signal.signal(signal.CTRL_C_EVENT, handler)


    while True:
        time.sleep(0.1)
        line = docker_log_p.stdout.readline()
        # line = docker_p_nice_stdout.readline().decode()
        match= re.search(r'https?://127.0.0.1\S+', line)
        if match:
            token_url = match.group(0)
            break

    webbrowser.open(token_url, new=1)

    print(f'JupyterLab should open in your browser. If not you can open it at this URL:\n\n    {token_url}.\n')
    
    print('To stop JupyterLab press Ctrl-C in this window.\n')

    for _ in range(60 * 60 * 24 * 365):
        try:
            time.sleep(1)
        except BaseException as e:
            with SuppressedKeyboardInterrupt():
                logging.debug('Jupyter server is stopping')
                docker_kill(run_container_id)
                docker_log_p.stdout.close()
                docker_log_p.kill()
                docker_run_p.kill()
                docker_log_p.wait()
                docker_run_p.wait()
                logging.debug('Jupyter server stopped')
                break
                # if e is KeyboardInterrupt:
                #     break
                # else:
                #     raise e

    print("JupyterLab no longer running. Close browser window.\n")




    # except BaseException as e:
    #     with DelayedKeyboardInterrupt():
    #         print('Service is stopping... ', end='', flush=True)
    #         docker_kill(run_container_id)
    #         docker_log_p.stdout.close()
    #         docker_log_p.kill()
    #         docker_run_p.kill()
    #         docker_log_p.wait()
    #         docker_run_p.wait()
    #         print('done.', flush=True)
    #     if e is not KeyboardInterrupt:
    #         raise e
    # # finally:
    # #     docker_kill(run_container_id)
    # #     if cleanup:
    # #         docker_cleanup()



        # docker system df
        # docker system df -v

        # docker system prune -a





            # from flask import Flask
            # app = Flask(__name__)

            # @app.route('/')
            # def display():
            #     return "Looks like it works!"

            # app.run(port=8888)



















# import signal
# os.kill(self.p.pid, signal.CTRL_C_EVENT)

    # stdout, stderr = docker_run_p.communicate()
    # if stdout:
    #     print(f'[stdout] {stdout}', end='', flush=True)
    # if stderr:
    #     print(f'[stderr] {stderr}', end='', flush=True, file=sys.stderr)



# JUST START DOCKER RUN WITH POPEN NONBLOCKING, THEN START DOCKER LOGS WITH POPEN NONBLOCKING, THEN READ FROM THIER STREAMS IN LOOP.


    # args = f"run --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()

    # proc = await asyncio.create_subprocess_exec('docker', args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)


# # USE RUNNER TO CAPTURE OUTPUT stream FROM 'docker logs --follow <container_id>'


# # if proc takes very long to complete, the CPUs are free to use cycles for 
# # other processes
# stdout, stderr = await proc.communicate()


    sys.exit()

    args = f"run --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()
    asyncio.run(run_docker(args))

    # container_id = subprocess.check_output('docker ps -q', shell=True).decode().strip()

    # args = f"docker logs --follow {container_id}".split()
    # asyncio.run(run_docker(args))


    # alternative
    #          -t -i
    # args = f"run --attach stdout --attach stderr --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main".split()

    # args = f"run -d --name kaspertest --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main  ; docker attach kaspertest".split()

    # args = f"run --pull=always --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()
    # args = f"run --rm --mount type=bind,source={user_home}/.ssh,target=/tmp/.ssh --mount type=bind,source={user_home}/.anaconda,target=/root/.anaconda --mount type=bind,source={pwd},target={pwd} -w {pwd} -i -t -p 8888:8888 {image_url}:main".split()

    # # args = f"run -t -i --attach stdout --attach stderr --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main".split()

    # asyncio.run(run_docker(args))

#docker run --attach stdout --attach stderr --name kaspertest --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main

#docker run -d --name kaspertest --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main ; docker attach kaspertes

# docker run -d --name topdemo alpine top -b

# docker attach topdemo

#docker run -d --name tester --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main -b

# docker run -d --name kaspertest --rm --mount type=bind,source=/Users/kmt/.ssh,target=/tmp/.ssh --mount type=bind,source=/Users/kmt/.anaconda,target=/root/.anaconda --mount type=bind,source=/Users/kmt/google_drive/projects/mbg-exercise-client,target=/Users/kmt/google_drive/projects/mbg-exercise-client -w /Users/kmt/google_drive/projects/mbg-exercise-client -p 8888:8888 registry.gitlab.au.dk/au81667/mbg-docker-exercises:main -b -t ; docker attach kaspertest

#     check_docker_running()

#     registry_listing = get_registry_listing()

# client.images.pull('kaspermunch/sap')

#     course_mapping = get_course_mapping()

#     course = get_user_input(course_mapping)

#     week_mapping = get_week_mapping()

#     check_no_other_exercise_container_running()

#     check_no_other_local_jupyter_running()

#     # https://docker-py.readthedocs.io/en/stable/
#     client = docker.from_env()
#     client.images.pull('nginx')
#     container = client.containers.run("bfirsh/reticulate-splines", detach=True)
#     for line in container.logs(stream=True):
#         print(line.strip())
#     container.stop()

#     launch_docker(course, week_mapping)

#     report_disk_space()

#     purge_docker_images_and_containers()


# #!/usr/bin/env python3

# import docker, getpass

# client = docker.from_env()

# my_pw = getpass.getpass(prompt='Password: ')

# sec_name = 'TestSec'
# noise = client.secrets.create(name=sec_name,  
#                               data=str.encode(my_pw))
# secret_id = client.secrets.list(filters={'name': sec_name})[0].id

# secRef = docker.types.SecretReference(secret_id, sec_name)

# print(type(secRef))

# client.services.create('alpine:latest',
#                        name='TestSvc',
#                        hostname='test_host',
#                        secrets=[secRef],
#                        command='sleep 999',)






# >>> import platform
# >>> platform.system()
# 'Darwin'
# >>> platform.processor()
# 'i386'
# >>> platform.platform()
# 'Darwin-10.8.0-i386-64bit'
# >>> platform.machine()
# 'i386'
# >>> platform.version()
# 'Darwin Kernel Version 10.8.0: Tue Jun  7 16:33:36 PDT 2011; root:xnu-1504.15.3~1/RELEASE_I386'
# >>> platform.uname()
# ('Darwin', 'Hostname.local', '10.8.0', 'Darwin Kernel Version 10.8.0: Tue Jun  7 16:33:36 PDT 2011; root:xnu-1504.15.3~1/RELEASE_I386', 'i386', 'i386')




# 1. Activate a MBGexercises environment  
# 2. Check for package updates of mbg-exercise-client package at the mbgexercises anaconda channel
# 3. Update package if necessary and reimport package after update to use new version  
# 4. Read registry listing using API requests library (see above)  
# 5. Read yml file mapping English to Danish course names (see above)
# 6. Take user input through to pick course
# 7. Read yml file mapping exercises to week numbers (see above)
# 8. Check that docker is installed
# 9. Check that docker is running  
# 10. Check that no other exercise container is running  
# 11. Check that no other local jupyter is using a port  
# 12. Launch docker run as a process in a separate thread (like in slurm-jupyter)  
# 13. Read URL from the output and launch the browser like in  (like in slurm-jupyter)  
# 14. Make sure the script cannot be shut down with keyboard interrupt or kill without cleaning up  
# 15. Report how much disk space images and containers currently use  
# 16. Ask to purge docker images and containers \[Y\]/n and do so  
# 17. Exit




# from collections import defaultdict
# from bullet import Bullet, colors, VerticalPrompt, SlidePrompt, ScrollBar, emojis

# options = dict(
#     indent = 0,
#     shift = 0,
#     align = 2, 
#     margin = 1,
#     # bullet = "★",
#     pointer = "★",
#     pad_right = 10,
#     height = 10,    
#     # bullet_color=colors.bright(colors.foreground["default"]),
#     word_color=colors.bright(colors.foreground["default"]),
#     word_on_switch=colors.bright(colors.foreground["green"]),
#     background_color=colors.background["default"],
#     background_on_switch=colors.background["default"],
#     return_index=False
# )

# image_name_list = [
#     'Biomolekylær_struktur_og_funktion-uge1-v1',
#     'Biomolekylær_struktur_og_funktion-uge2-v1',
#     'Bioinformatik_og_programmering-uge_1-v1',
#     'Bioinformatik_og_programmering-uge_2-v1',
# ]

# image_tree = defaultdict(lambda: defaultdict(lambda: defaultdict(str)))
# for image_name in image_name_list:
#     c, w, v = image_name.split('-')
#     image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name

# # cli = ScrollBar(
# #     "How are you feeling today? ", 
# #     choices = list(image_tree.keys()) + ['asdf']*15,
# #     height = 15,
# #     **options
# # )
# # result = cli.launch()
# # print(result)

# cli = ScrollBar(prompt = "\n Select course: ", choices = list(image_tree.keys())*15, **options)
# course = cli.launch()
# cli = ScrollBar(prompt = "\n Select exercise: ", choices = list(image_tree[course].keys()), **options)
# week = cli.launch()
# cli = ScrollBar(prompt = "\n Select version: ", choices = list(image_tree[course][week].keys()), **options)
# version = cli.launch()
# selected_image = image_tree[course][week][version]


# # cli = SlidePrompt([
# #     Bullet(prompt = "\nSelect course: ", choices = list(image_tree.keys()), **options),
# #     Bullet(prompt = "\nSelect week: ", choices = list(image_tree[course].keys()), **options),
# #     Bullet(prompt = "\nSelect version: ", choices = list(image_tree[course][week].keys()), **options)
# # ])
# # course, week, version = cli.launch()
# # selected_image = image_tree[course][week][version]




# # course_menu = Bullet(
# #         prompt = "\nSelect course: ",
# #         choices = ["Biomolekylær struktur og funktion", "Bioinformatik og programmering", "orange", "watermelon", "strawberry"], 
# #         indent = 3,
# #         shift = 0,
# #         align = 3, 
# #         margin = 1,
# #         bullet = "★",
# #         # bullet_color=colors.bright(colors.foreground["cyan"]),
# #         # word_color=colors.bright(colors.foreground["yellow"]),
# #         # word_on_switch=colors.bright(colors.foreground["yellow"]),
# #         # background_color=colors.background["black"],
# #         # background_on_switch=colors.background["black"],
# #         pad_right = 10
# #     )
# # week_menu = Bullet(
# #         prompt = "\nSelect week: ",
# #         choices = ["week1", "week2"], 
# #         indent = 3,
# #         shift = 0,
# #         align = 3, 
# #         margin = 1,
# #         bullet = "★",
# #         # bullet_color=colors.bright(colors.foreground["cyan"]),
# #         # word_color=colors.bright(colors.foreground["yellow"]),
# #         # word_on_switch=colors.bright(colors.foreground["yellow"]),
# #         # background_color=colors.background["black"],
# #         # background_on_switch=colors.background["black"],
# #         pad_right = 10
# #     )


# # cli = VerticalPrompt([course_menu, week_menu], spacing = 0)

# # result = cli.launch()
# # print("You chose:", result)

# # # result = cli.launch()
# # # print(result)

# adapters
# api_version
# attach
# attach_socket
# auth
# base_url
# build
# cert
# close
# commit
# connect_container_to_network
# containers
# cookies
# copy
# create_container
# create_container_config
# create_container_from_config
# create_endpoint_config
# create_host_config
# create_network
# create_networking_config
# create_service
# create_swarm_spec
# create_volume
# delete
# diff
# disconnect_container_from_network
# events
# exec_create
# exec_inspect
# exec_resize
# exec_start
# export
# from_env
# get
# get_adapter
# get_archive
# get_image
# get_redirect_target
# head
# headers
# history
# hooks
# images
# import_image
# import_image_from_data
# import_image_from_file
# import_image_from_image
# import_image_from_stream
# import_image_from_url
# info
# init_swarm
# insert
# inspect_container
# inspect_image
# inspect_network
# inspect_node
# inspect_service
# inspect_swarm
# inspect_task
# inspect_volume
# join_swarm
# kill
# leave_swarm
# load_image
# login
# logs
# max_redirects
# merge_environment_settings
# mount
# networks
# nodes
# options
# params
# patch
# pause
# ping
# port
# post
# prepare_request
# proxies
# pull
# push
# put
# put_archive
# rebuild_auth
# rebuild_method
# rebuild_proxies
# remove_container
# remove_image
# remove_network
# remove_service
# remove_volume
# rename
# request
# resize
# resolve_redirects
# restart
# search
# send
# services
# should_strip_auth
# start
# stats
# stop
# stream
# tag
# tasks
# timeout
# top
# trust_env
# unpause
# update_container
# update_service
# update_swarm
# verify
# version
# volumes
# wait





    # # client = docker.Client(base_url='https://registry.hub.docker.com:443')
    # client = docker.Client(
    #     base_url='tcp://gitlab.au.dk:443',
    #     # base_url='tcp://gitlab.au.dk:443/api/v4/projects/au81667%2Fmbg-docker-exercises/registry/repositories',
    #     # credstore_env={'PRIVATE-TOKEN': 'glpat-tiYpz3zJ95qzVXnyN8--'}
    #     )
    # print(client.images())
    # print(client.search('au81667/mbg-docker-exercises'))
    # client.search('kaspermunch/sap')

#     # client = docker.Client(base_url='https://registry.hub.docker.com:443')
#     client = docker.Client(base_url='https://registry.gitlab.au.dk:443')

# #    client.images(name='kaspermunch/sap')
#     client.search('au81667/mbg-docker-exercises')

#    docker pull registry.gitlab.au.dk/au81667/mbg-docker-exercises:main




    # headers = {'PRIVATE-TOKEN': 'glpat-tiYpz3zJ95qzVXnyN8--'}
    # client.get('au81667/mbg-docker-exercises', **headers)



#registry.gitlab.au.dk/au81667/mbg-docker-exercises

    # print(dir(docker.constants))

#    print(client.pull('mbg-docker-exercises'))#, auth_config={'PRIVATE-TOKEN': 'glpat-tiYpz3zJ95qzVXnyN8--'}))
    # print(*dir(client), sep='\n')

    # noise = docker.secrets()#.create_secret(name='PRIVATE-TOKEN',  
    #                          #  data=str.encode('glpat-tiYpz3zJ95qzVXnyN8--'))

    # import  getpass
    # client = docker.from_env()
    # my_pw = getpass.getpass(prompt='Password: ')
    # sec_name = 'TestSec'
    # noise = docker.secrets.create(name=sec_name,  
    #                             data=str.encode(my_pw))
    # secret_id = docker.secrets.list(filters={'name': sec_name})[0].id

    # secRef = docker.types.SecretReference(secret_id, sec_name)

    # print(type(secRef))

    # client.services.create('alpine:latest',
    #                     name='TestSvc',
    #                     hostname='test_host',
    #                     secrets=[secRef],
    #                     command='sleep 999',)



