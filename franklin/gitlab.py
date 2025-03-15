import requests
from .config import GITLAB_API_URL, GITLAB_GROUP, GITLAB_TOKEN
from . import utils
from . import cutie

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


def pick_course():
    course_names = get_course_names()
    course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
    utils.secho("\nUse arrow keys to select course and press Enter:", fg='green')
    captions = []
    course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
    return course_group_names[course_idx], course_danish_names[course_idx]