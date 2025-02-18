import platform
import subprocess
from subprocess import DEVNULL
import json
import click
import shutil
import psutil
import requests
from .utils import format_cmd
from .config import REGISTRY_BASE_URL, GITLAB_GROUP
from . import cutie
from .gitlab import get_course_names, get_exercise_names


def installed():
    if platform.system() == 'Darwin':
        return shutil.which('docker')
    if platform.system() == 'Linux':
        return shutil.which('docker')
    if platform.system() == 'Windows':
        return shutil.which('docker')
    return False



def free_disk_space():
    return shutil.disk_usage('/').free / 1024**3

def check_docker_desktop_running():
    
    processes = [p.name() for p in psutil.process_iter() if 'docker desktop' in p.name().lower()]
    if not processes:
        return False
    return True


def check_internet_connection():
    try:
        request = requests.get("https://hub.docker.com/", timeout=2)
        return True
    except (requests.ConnectionError, requests.Timeout) as exception:
        return False


def command(command, silent=False, return_json=False):
    if silent:
        return subprocess.run(format_cmd(command), check=False, stdout=DEVNULL, stderr=DEVNULL)
    if return_json:
        result = []
        for line in subprocess.check_output(format_cmd(command + ' --format json')).decode().strip().splitlines():
            result.append(json.loads(line))
        return result
    else:
        return subprocess.check_output(format_cmd(command)).decode().strip()


def volumes(return_json=False):
    return command('docker volume ls', return_json=return_json)


def images(return_json=False):
    return command('docker images', return_json=return_json)


def pull(image_url):
    subprocess.run(format_cmd(f'docker pull {image_url}:main'), check=False,
                    # stdout=DEVNULL, stderr=DEVNULL
                    )

    # # return os.system(f'docker pull {image_url}:main')

    # # ps = subprocess.Popen(format_cmd(f"docker pull {image_url}:main"), stdout=subprocess.PIPE)
    # # # output = subprocess.check_output(format_cmd("grep -v 'Digest\|Status\|What\|View'"), stdin=ps.stdout)
    # # subprocess.run(format_cmd("grep -v 'Digest\|Status\|What\|View'"), stdin=ps.stdout)
    # # ps.wait()


def containers(return_json=False):
    return command('docker ps', return_json=return_json)


def remove_images():
    img = images(return_json=True)
    if not img:
        click.echo("\nNo images to remove\n")
        return

    course_names = get_course_names()
    exercise_names = {}

    header = ['Course', 'Exercise', 'Created', 'Size', 'ID']
    table = []
    prefix = f'{REGISTRY_BASE_URL}/{GITLAB_GROUP}'
    for img in images(return_json=True):
        if img['Repository'].startswith(prefix):

            rep = img['Repository'].replace(prefix, '')
            if rep.startswith('/'):
                rep = rep[1:]
            course_label, exercise_label = rep.split('/')
            if exercise_label not in exercise_names:
                exercise_names.update(get_exercise_names(course_label))
            course_name = course_names[course_label]
            exercise_name = exercise_names[exercise_label]
            course_field = course_field[:20]+'...' if len(course_name) > 23 else course_name
            table.append((course_names[course_label], exercise_names[exercise_label], img['CreatedSince'], img['Size'], img['ID']))

    col_widths = [max(len(x) for x in col) for col in zip(*table)]

    table_width = sum(col_widths) + 4 * len(col_widths) + 2
    # print(table_width)
    click.secho("\nChoose images to remove:", fg='green')

    click.echo("\nUse arrows to move highlight and space to select/deselect one or more images. Press enter to remove \n")

    click.echo('    | '+'| '.join([x.ljust(w+2) for x, w in zip(header, col_widths)]))
    click.echo('-'*table_width)
    rows = []
    for row in table:
        rows.append('| '+'| '.join([x.ljust(w+2) for x, w in zip(row, col_widths)]))
    captions = []
    selected_indices = cutie.select_multiple(
        rows, caption_indices=captions, 
        # hide_confirm=False
    )
    for img_id in [table[i][-1] for i in selected_indices]:
        rm_image(img_id, force=True)

    # print([image_ids[i] for i in selected_indices])

# [{'Containers': 'N/A', 
#   'CreatedAt': '2024-08-30 18:51:38 +0200 CEST', 
#   'CreatedSince': '5 months ago', 
#   'Digest': '<none>', 
#   'ID': '3523f5255b8d', 
#   'Repository': 'registry.gitlab.au.dk/mbg-exercises/experimental-molecular-biology/molecular_biology_ii-chipseq-exercise', 
#   'SharedSize': 'N/A', 
#   'Size': '3.09GB', 'Tag': 'main', 'UniqueSize': 'N/A', 'VirtualSize': '3.091GB'}]a


#     print(img)

#     nemeses_options = [
#         "The French",
#         "The Police",
#         "The Knights Who Say Ni",
#         "Women",
#         "The Black Knight",
#         "The Bridge Keeper",
#     ]
#     print("Choose your nemeses")
#     # Choose multiple options from a list
#     nemeses_indices = cutie.select_multiple(
#         nemeses_options, caption_indices=[6], hide_confirm=False
#     )
#     nemeses = [
#         nemesis
#         for nemesis_index, nemesis in enumerate(nemeses_options)
#         if nemesis_index in nemeses_indices
#     ]
#     click.echo(nemeses)


def prune_containers():
    command(f'docker container prune --filter="Name={REGISTRY_BASE_URL}*"', silent=True)


def prune_volumes():
    command(f'docker volume --filter="Name={REGISTRY_BASE_URL}*"')


def prune_all():
    command(f'docker prune -a', silent=True)


def rm_image(image, force=False):
    if force:
        command(f'docker image rm -f {image}', silent=True)
    else:
        command(f'docker image rm {image}', silent=True)


def kill(container_id):
    command(f'docker kill {container_id}', silent=True)


def cleanup():
    for image in images():
        if image['Repository'].startswith(REGISTRY_BASE_URL):
            rm_image(image['ID'])
    prune_containers()
    prune_volumes()
    prune_all()


def storage(verbose=False):
    if verbose:
        return command(f'docker system df -v')
    return command(f'docker system df')


def image_exists(image_url):
    for image in images(return_json=True):
        if image['Repository'].startswith(image_url):
            return True
    return False
