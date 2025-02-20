
from . import cutie
import time
import requests
from .config import GITLAB_API_URL, GITLAB_GROUP, GITLAB_TOKEN
import click
import shutil
from . import utils
from .gitlab import get_course_names, get_exercise_names

# def select_image(exercises_images):

#     # print(exercise_list)
#     # image_tree = defaultdict(lambda: defaultdict(str))
#     # for course, exercise in exercise_dict:
#     #     # c, w, v = image_name.split('-')
#     #     # image_tree[c.replace('_', ' ')][w.replace('_', ' ')][v.replace('_', ' ')] = image_name
#     #     image_tree[course][exercise] = image_name

#     utils.echo(click.wrap_text("\n\nUse arrow keys to move and enter to select"
#                                "Press Ctrl-C to close the application.", width=max((shutil.get_terminal_size().columns)/2, 70), 
#                initial_indent='', subsequent_indent='', 
#                preserve_paragraphs=True))   
    

#     def pick_course():
#         course_names = get_course_names()
#         course_group_names, course_danish_names,  = zip(*sorted(course_names.items()))
#         utils.secho("\nSelect course:", fg='green')
#         captions = []
#         # options = list(image_tree.keys())
#         # course = options[cutie.select(options, caption_indices=captions, selected_index=0)]
#         course_idx = cutie.select(course_danish_names, caption_indices=captions, selected_index=0)
#         return course_group_names[course_idx], course_danish_names[course_idx]

#     while True:
#         course, danish_course_name = pick_course()

#         exercise_names = get_exercise_names(course)

#         # only use those with listed images
#         for key in list(exercise_names.keys()):
#             if (course, key) not in exercises_images:
#                 del exercise_names[key]

#         if exercise_names:
#             break

#         utils.secho(f"\n  >>No exercises for {danish_course_name}<<", fg='red')

#     exercise_repo_names, exercise_danish_names = zip(*sorted(exercise_names.items()))
#     utils.secho(f"\nSelect exercise in {danish_course_name}:", fg='green')
#     captions = []
#     # options = list(image_tree[course].keys())
#     # week = options[cutie.select(options, caption_indices=captions, selected_index=0)]
#     exercise_idx = cutie.select(exercise_danish_names, caption_indices=captions, selected_index=0)
#     exercise = exercise_repo_names[exercise_idx]
#     # print("\nSelect exercise:")
#     # captions = []
#     # options = list(image_tree[course][week].keys())
#     # exercise = options[cutie.select(options, caption_indices=captions, selected_index=0)]

#     utils.echo(f"\nPreparing jupyter session for:\n")
#     utils.echo(f"    {danish_course_name}: {exercise_danish_names[exercise_idx]} \n")
#     time.sleep(1)

#     selected_image = exercises_images[(course, exercise)]
#     return selected_image


# def get_registry_listing(registry):
#     s = requests.Session()
#     # s.auth = ('user', 'pass')
#     s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
#     # s.headers.update({'PRIVATE-TOKEN': 'glpat-BmHo-Fh5R\_TvsTHqojzz'})
#     images = {}
#     r  = s.get(registry,  headers={ "Content-Type" : "application/json"})
#     if not r.ok:
#       r.raise_for_status()
#     for entry in r.json():
#         group, course, exercise = entry['path'].split('/')
#         images[(course, exercise)] = entry['location']
#         # images[(course, exercise)] = entry#['location']
#     return images


# def get_course_names():
#     s = requests.Session()
#     s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
#     url = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}/subgroups'
# #https://gitlab.au.dk/api/v4/groups/mbg-exercises/subgroups

#     name_mapping = {}
#     r  = s.get(url, headers={ "Content-Type" : "application/json"})
#     if not r.ok:
#         r.raise_for_status()

#     for entry in r.json():
#         if 'template' in entry['path'].lower():
#             continue
#         if entry['description']:
#             name_mapping[entry['path']] = entry['description']
#         else:
#             name_mapping[entry['path']] = entry['path']
    
#     return name_mapping


# def get_exercise_names(course):
#     s = requests.Session()
#     s.headers.update({'PRIVATE-TOKEN': GITLAB_TOKEN})
#     url = f'{GITLAB_API_URL}/groups/{GITLAB_GROUP}%2F{course}/projects'

#     name_mapping = {}
#     r  = s.get(url, headers={ "Content-Type" : "application/json"})
#     if not r.ok:
#         r.raise_for_status()

#     for entry in r.json():
#         if entry['description']:
#             name_mapping[entry['path']] = entry['description']
#         else:
#             name_mapping[entry['path']] = entry['path']
    
#     return name_mapping
