import sys, os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbclient import NotebookClient

from .utils import run_cmd

source = '''
import types
def imports():
    for name, val in globals().items():
        if isinstance(val, types.ModuleType):
            yield val.__name__
        elif isinstance(val, types.FunctionType):
            if hasattr(val, '__module__') and val.__module__ != 'builtins':
                yield val.__module__
        elif isinstance(val, types.BuiltinFunctionType):
            if val.__module__ != 'builtins':
                yield val.__module__
        elif isinstance(val, types.BuiltinMethodType):
            if val.__self__.__class__.__module__ != 'builtins':
                yield val.__self__.__class__.__module__
        # if isinstance(val, types.ModuleType) and val.__name__ != 'builtins':
        #     yield val.__name__
list(imports())
'''

def get_notebook_dependencies(filename: str) -> list:

    with open(filename) as ff:
        nb = nbformat.read(ff, nbformat.NO_CONVERT)
        # nb = nbformat.read(ff, as_version=4)

    d = {'cell_type': 'code', 'execution_count': None, 
    'metadata': {}, 'outputs': [], 'source': source}

    nb['cells'].append(nbformat.from_dict(d))

    client = NotebookClient(nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': '.'}})
    client.execute()
    # nbformat.write(nb, 'executed_notebook.ipynb')

    names = eval(nb['cells'][-1]['outputs'][0]['data']['text/plain'])

    modules = []
    for n in names:
        if n not in sys.builtin_module_names and not n.startswith('_'):
            modules.append(n.split('.')[0])

    return modules


def update_pixi(modules: list):

    if not os.path.exists('pixi.toml'):
        run_cmd('pixi init')
    run_cmd('pixi add ' + ' '.join(modules))


def update_dependencies(filename: str):
    modules = get_notebook_dependencies(filename)
    update_pixi(modules)

    # #print(type(nb_in['cells'][0]))    
    # ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

    # nb_out = ep.preprocess(nb)

    # print(nb_out)
    # #print(nb_out['cells'][-1]['outputs'])




import io, os, sys, types
from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell

def find_notebook(fullname, path=None):
    """find a notebook, given its fully qualified name and an optional path

    This turns "foo.bar" into "foo/bar.ipynb"
    and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
    does not exist.
    """
    name = fullname.rsplit('.', 1)[-1]
    if not path:
        path = ['']
    for d in path:
        nb_path = os.path.join(d, name + ".ipynb")
        if os.path.isfile(nb_path):
            return nb_path
        # let import Notebook_Name find "Notebook Name.ipynb"
        nb_path = nb_path.replace("_", " ")
        if os.path.isfile(nb_path):
            return nb_path
        
class NotebookLoader(object):
    """Module Loader for Jupyter Notebooks"""

    def __init__(self, path=None):
        self.shell = InteractiveShell.instance()
        self.path = path

    def load_module(self, fullname):
        """import a notebook as a module"""
        path = find_notebook(fullname, self.path)

        print("importing Jupyter notebook from %s" % path)

        # load the notebook object
        with io.open(path, 'r', encoding='utf-8') as f:
            nb = read(f, 4)

        # create the module and add it to sys.modules
        # if name in sys.modules:
        #    return sys.modules[name]
        mod = types.ModuleType(fullname)
        mod.__file__ = path
        mod.__loader__ = self
        mod.__dict__['get_ipython'] = get_ipython
        sys.modules[fullname] = mod

        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        save_user_ns = self.shell.user_ns
        self.shell.user_ns = mod.__dict__

        try:
            for cell in nb.cells:
                if cell.cell_type == 'code':
                    # transform the input to executable Python
                    code = self.shell.input_transformer_manager.transform_cell(cell.source)
                    # run the code in themodule
                    exec(code, mod.__dict__)
        finally:
            self.shell.user_ns = save_user_ns


class NotebookFinder(object):
    """Module finder that locates Jupyter Notebooks"""

    def __init__(self):
        self.loaders = {}

    def find_module(self, fullname, path=None):
        nb_path = find_notebook(fullname, path)
        if not nb_path:
            return

        key = path
        if path:
            # lists aren't hashable
            key = os.path.sep.join(path)

        if key not in self.loaders:
            self.loaders[key] = NotebookLoader(path)
        return self.loaders[key]            
    
# sys.meta_path.append(NotebookFinder())    

# I guess i can import the notebook as module

# Get the globals from teh ModuleNotFoundError

# and

# # get the list of imports in the current module
# import types
# def imports():
#     for name, val in globals().items():
#         if isinstance(val, types.ModuleType):
#             yield val.__name__
# list(imports())    