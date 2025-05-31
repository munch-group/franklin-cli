import sys, os, re
import nbformat
import nbformat
from pathlib import Path
# import importlib_resources
import subprocess, shlex, shutil


py_to_conda_package_map = {
    "sklearn": "scikit-learn",
    "cv2": "opencv",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "Crypto": "pycryptodome",
    "Bio": "biopython",
    "dateutil": "python-dateutil",
    "pkg_resources": "setuptools",
    "zmq": "pyzmq",
    "IPython": "ipython",
    "ipykernel": "ipykernel",
    "traitlets": "traitlets",
    "jupyter_core": "jupyter_core",
    "jupyter_client": "jupyter_client",
    "nbconvert": "nbconvert",
    "nbformat": "nbformat",
    "widgetsnbextension": "widgetsnbextension",
    "skimage": "scikit-image",
    "pandas_datareader": "pandas-datareader",
    "typing_extensions": "typing-extensions",
    "sentence_transformers": "sentence-transformers",
    "mpl_toolkits": "matplotlib",
    "lxml.etree": "lxml",
    "ujson": "ujson",
    "pyarrow": "pyarrow",
    "pyproj": "pyproj",
    "shapely.geometry": "shapely",
    "osgeo": "gdal",
    "netCDF4": "netcdf4",
    "h5netcdf": "h5netcdf",
    "pydantic_core": "pydantic-core",
    "pymc3": "pymc3",
    "pymc": "pymc",
    "xarray.core": "xarray",
    "cartopy.crs": "cartopy",
    "geopandas.tools": "geopandas",
    "pygeos.lib": "pygeos",
    "fiona.collection": "fiona",
    "rasterio.plot": "rasterio",
    "pyogrio": "pyogrio",
    "vtkmodules": "vtk",
    "OpenGL.GL": "pyopengl",
    "OpenGL_accelerate": "pyopengl-accelerate",
    "PyQt5": "pyqt",
    "PyQt6": "pyqt",
    "PySide2": "pyside2",
    "PySide6": "pyside6",
    "PyQtWebEngine": "pyqtwebengine",
    "pyqtchart": "pyqtchart",
    "pyqt3d": "pyqt3d",
    "pyqt5_tools": "pyqt5-tools",
    "pyqt6_tools": "pyqt6-tools",
    "pyqt5_sip": "pyqt5-sip",
    "pyqt6_sip": "pyqt6-sip",
    "sipbuild": "sip",
    "bqplot_gl": "bqplot-gl",
    "ipyvolume.pylab": "ipyvolume",
    "k3d.plot": "k3d",
    "traittypes": "traittypes",
    "ipywebrtc": "ipywebrtc",
    "jupyterlab_widgets": "jupyterlab-widgets",
    "ipyevents": "ipyevents",
    "ipycanvas": "ipycanvas",
    "ipympl": "ipympl",
    "ipytree": "ipytree",
    "ipycytoscape": "ipycytoscape",
    "ipysheet": "ipysheet",
    "nbdime.diffing": "nbdime",
    "nbgitpuller": "nbgitpuller",
    "jupyter_server": "jupyter_server",
    "jupyterlab_server": "jupyterlab_server",
    "voila_gridstack": "voila-gridstack",
    "voila_material": "voila-material",
    "voila_vuetify": "voila-vuetify",
    "bqplot_image_gl": "bqplot-image-gl",
    "dash_bootstrap_components": "dash-bootstrap-components",
    "dash_core_components": "dash-core-components",
    "dash_html_components": "dash-html-components",
    "dash_table": "dash-table",
    "plotly.graph_objects": "plotly",
    "altair.vegalite.v4": "altair",
    "seaborn.axisgrid": "seaborn",
    "statsmodels.api": "statsmodels",
    "line_profiler": "line_profiler",
    "memory_profiler": "memory_profiler",
    "snakeviz": "snakeviz",
    "tensorboardX": "tensorboardx",
    "tensorflow_hub": "tensorflow-hub",
    "tensorflow_datasets": "tensorflow-datasets",
    "tf_agents": "tf-agents",
    "jaxlib.pocketfft": "jaxlib",
    "jax.numpy": "jax",
    "flax.linen": "flax",
    "optax": "optax",
    "chex": "chex",
    "haiku": "dm-haiku",
    "transformers.modeling_utils": "transformers",
    "datasets.load": "datasets",
    "evaluate.metrics": "evaluate",
    "accelerate.state": "accelerate",
    "scvi": "scvi-tools",
    "anndata._core": "anndata",
    "scanpy.tools": "scanpy",
    "muon._core": "muon"
}

r_to_conda_package_map = {
    "ggplot2": "r-ggplot2",
    "dplyr": "r-dplyr",
    "tidyr": "r-tidyr",
    "readr": "r-readr",
    "purrr": "r-purrr",
    "tibble": "r-tibble",
    "stringr": "r-stringr",
    "forcats": "r-forcats",
    "lubridate": "r-lubridate",
    "magrittr": "r-magrittr",
    "rlang": "r-rlang",
    "glue": "r-glue",
    "broom": "r-broom",
    "readxl": "r-readxl",
    "haven": "r-haven",
    "httr": "r-httr",
    "xml2": "r-xml2",
    "jsonlite": "r-jsonlite",
    "rvest": "r-rvest",
    "shiny": "r-shiny",
    "shinydashboard": "r-shinydashboard",
    "plotly": "r-plotly",
    "leaflet": "r-leaflet",
    "DT": "r-dt",
    "data.table": "r-data.table",
    "sf": "r-sf",
    "sp": "r-sp",
    "rgdal": "r-rgdal",
    "rgeos": "r-rgeos",
    "maptools": "r-maptools",
    "maps": "r-maps",
    "ggmap": "r-ggmap",
    "ggthemes": "r-ggthemes",
    "ggrepel": "r-ggrepel",
    "scales": "r-scales",
    "cowplot": "r-cowplot",
    "gridExtra": "r-gridextra",
    "ggridges": "r-ggridges",
    "viridis": "r-viridis",
    "RColorBrewer": "r-rcolorbrewer",
    "reshape2": "r-reshape2",
    "janitor": "r-janitor",
    "skimr": "r-skimr",
    "knitr": "r-knitr",
    "rmarkdown": "r-rmarkdown",
    "bookdown": "r-bookdown",
    "blogdown": "r-blogdown",
    "tinytex": "r-tinytex",
    "kableExtra": "r-kableextra",
    "xtable": "r-xtable",
    "officer": "r-officer",
    "flextable": "r-flextable",
    "survival": "r-survival",
    "caret": "r-caret",
    "randomForest": "r-randomforest",
    "xgboost": "r-xgboost",
    "e1071": "r-e1071",
    "nnet": "r-nnet",
    "glmnet": "r-glmnet",
    "mlr": "r-mlr",
    "mlr3": "r-mlr3",
    "lme4": "r-lme4",
    "nlme": "r-nlme",
    "MASS": "r-mass",
    "car": "r-car",
    "multcomp": "r-multcomp",
    "AER": "r-aer",
    "zoo": "r-zoo",
    "xts": "r-xts",
    "forecast": "r-forecast",
    "tseries": "r-tseries",
    "quantmod": "r-quantmod",
    "timeDate": "r-timedate",
    "lubridate": "r-lubridate",
    "tsibble": "r-tsibble",
    "fable": "r-fable",
    "prophet": "r-prophet",
    "igraph": "r-igraph",
    "ggraph": "r-ggraph",
    "networkD3": "r-networkd3",
    "visNetwork": "r-visnetwork",
    "DiagrammeR": "r-diagrammer",
    "gplots": "r-gplots",
    "corrplot": "r-corrplot",
    "pheatmap": "r-pheatmap",
    "ComplexHeatmap": "r-complexheatmap",
    "VennDiagram": "r-venndiagram",
    "UpSetR": "r-upsetr",
    "ggpubr": "r-ggpubr",
    "ggfortify": "r-ggfortify",
    "factoextra": "r-factoextra",
    "FactoMineR": "r-factominer",
    "psych": "r-psych",
    "Hmisc": "r-hmisc",
    "corrgram": "r-corrgram",
    "PerformanceAnalytics": "r-performanceanalytics",
    "stargazer": "r-stargazer",
    "texreg": "r-texreg",
    "plm": "r-plm",
    "sandwich": "r-sandwich",
    "lmtest": "r-lmtest",
    "AICcmodavg": "r-aiccmodavg",
    "MuMIn": "r-mumin",
    "boot": "r-boot",
    "survey": "r-survey",
    "weights": "r-weights",
    "srvyr": "r-srvyr",
    "gmodels": "r-gmodels",
    "vcd": "r-vcd",
    "MCMCpack": "r-mcmcpack",
    "coda": "r-coda"
}


def get_notebook_dependencies(filename: Path) -> list:

    with open(filename) as ff:
        nb = nbformat.read(ff, nbformat.NO_CONVERT)

    py_modules = []
    r_modules = []
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            if not cell['source'].strip() or cell['source'].startswith('%'):
                continue
        # R
        r_modules.extend(
            re.findall(r'''library\s*\(['"]([a-zA-Z0-9_.]+)['"]\)''', 
                       cell['source']))

        # Python
        for line in cell['source'].split('\n'):
            line = line.strip()
            if line.startswith('#'):
                continue
            words = re.split(r'(?<!,)\s+(?!,)', line)
            if len(words) >= 2:
                if words[0] == 'from':                    
                    py_modules.append(words[1].split('.')[0])
                elif words[0] == 'import':
                    if ',' not in words[1]:
                        py_modules.append(words[1].split('.')[0])
                    else:
                        for x in re.split(r'\s*,\s*', line):
                            if x:
                                py_modules.append(x.split('.')[0])
    
    dependencies = []
    for m in py_modules:
        if m not in sys.stdlib_module_names and not m.startswith('_'):
            dependencies.append(py_to_conda_package_map.get(m, m))
    for m in r_modules:
        dependencies.append(r_to_conda_package_map.get(m, m))

    return dependencies

if __name__ == '__main__':

    # read arguments from command line
    import argparse
    parser = argparse.ArgumentParser(description='Update pixi dependencies from Jupyter notebooks.')
    parser.add_argument('root', type=Path, help='The root dir with notebooks.')
    args = parser.parse_args()
    assert args.root.is_dir(), f"Root directory {args.root} does not exist or is not a directory."

    dependencies = []
    for path in args.root.glob('**/*.ipynb'):
        dependencies.extend(get_notebook_dependencies(path))
    dependencies = list(set(dependencies))  # remove duplicates

    os.chdir(args.root)

    if not Path('pixi.toml').exists():
        path = os.path.dirname(sys.modules['franklin'].__file__) + '/data/templates/exercise/pixi.toml'
        shutil.copy(path, 'pixi.toml')

        # for p in importlib_resources.files().joinpath('data/templates/exercise').iterdir():
        #     if p.name == 'pixi.toml':
        #         shutil.copy(p, 'pixi.toml')
        #         break

    if any(x.startswith('r-') for x in dependencies):
        cmd = 'pixi workspace channel add r'
        cmd = shlex.split(cmd)
        cmd[0] = shutil.which(cmd[0])
        subprocess.run(cmd, check=True)

    cmd = 'pixi add --feature exercise.target.linux-64 ' + ' '.join(dependencies)
    cmd = shlex.split(cmd)
    cmd[0] = shutil.which(cmd[0])
    subprocess.run(cmd, check=True)







# def get_notebook_dependencies(filename: Path) -> list:

    # with open(filename) as ff:
    #     nb = nbformat.read(ff, nbformat.NO_CONVERT)

    # with open('pixi-cell.py', 'r') as f:
    #     source = f.read()

#     source '''
# import inspect, sys

# def imports():
#     for val in globals().values():
#         try:
#             module = inspect.getmodule(val)            
#         except TypeError:
#             continue
#         if module:
#             name = module.__name__.split('.')[0]
#             if name not in sys.stdlib_module_names:
#                 yield name

# list(imports())    
#     '''

#     d = {'cell_type': 'code', 'execution_count': None, 
#     'metadata': {}, 'outputs': [], 'source': source}


    # modules = [module_to_conda_package.get(m, m) for m in modules]



    # nb['cells'].append(nbformat.from_dict(d))

    # client = NotebookClient(nb, timeout=600, kernel_name='python3', resources={'metadata': {'path': '.'}})
    # client.execute()

    # names = eval(nb['cells'][-1]['outputs'][0]['data']['text/plain'])
    # modules = []
    # for n in names:
    #     if n not in sys.builtin_module_names and not n.startswith('_'):
    #         modules.append(n.split('.')[0])
    # modules = list(set(modules))  # remove duplicates
    # modules = [module_to_conda_package.get(m, m) for m in modules]
    # return modules





    # #print(type(nb_in['cells'][0]))    
    # ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

    # nb_out = ep.preprocess(nb)

    # print(nb_out)
    # #print(nb_out['cells'][-1]['outputs'])




# import io, os, sys, types
# from IPython import get_ipython
# from nbformat import read
# from IPython.core.interactiveshell import InteractiveShell

# def find_notebook(fullname, path=None):
#     """find a notebook, given its fully qualified name and an optional path

#     This turns "foo.bar" into "foo/bar.ipynb"
#     and tries turning "Foo_Bar" into "Foo Bar" if Foo_Bar
#     does not exist.
#     """
#     name = fullname.rsplit('.', 1)[-1]
#     if not path:
#         path = ['']
#     for d in path:
#         nb_path = os.path.join(d, name + ".ipynb")
#         if os.path.isfile(nb_path):
#             return nb_path
#         # let import Notebook_Name find "Notebook Name.ipynb"
#         nb_path = nb_path.replace("_", " ")
#         if os.path.isfile(nb_path):
#             return nb_path
        
# class NotebookLoader(object):
#     """Module Loader for Jupyter Notebooks"""

#     def __init__(self, path=None):
#         self.shell = InteractiveShell.instance()
#         self.path = path

#     def load_module(self, fullname):
#         """import a notebook as a module"""
#         path = find_notebook(fullname, self.path)

#         print("importing Jupyter notebook from %s" % path)

#         # load the notebook object
#         with io.open(path, 'r', encoding='utf-8') as f:
#             nb = read(f, 4)

#         # create the module and add it to sys.modules
#         # if name in sys.modules:
#         #    return sys.modules[name]
#         mod = types.ModuleType(fullname)
#         mod.__file__ = path
#         mod.__loader__ = self
#         mod.__dict__['get_ipython'] = get_ipython
#         sys.modules[fullname] = mod

#         # extra work to ensure that magics that would affect the user_ns
#         # actually affect the notebook module's ns
#         save_user_ns = self.shell.user_ns
#         self.shell.user_ns = mod.__dict__

#         try:
#             for cell in nb.cells:
#                 if cell.cell_type == 'code':
#                     # transform the input to executable Python
#                     code = self.shell.input_transformer_manager.transform_cell(cell.source)
#                     # run the code in themodule
#                     exec(code, mod.__dict__)
#         finally:
#             self.shell.user_ns = save_user_ns


# class NotebookFinder(object):
#     """Module finder that locates Jupyter Notebooks"""

#     def __init__(self):
#         self.loaders = {}

#     def find_module(self, fullname, path=None):
#         nb_path = find_notebook(fullname, path)
#         if not nb_path:
#             return

#         key = path
#         if path:
#             # lists aren't hashable
#             key = os.path.sep.join(path)

#         if key not in self.loaders:
#             self.loaders[key] = NotebookLoader(path)
#         return self.loaders[key]            
    
# # sys.meta_path.append(NotebookFinder())    

# # I guess i can import the notebook as module

# # Get the globals from teh ModuleNotFoundError

# # and

# # # get the list of imports in the current module
# # import types
# # def imports():
# #     for name, val in globals().items():
# #         if isinstance(val, types.ModuleType):
# #             yield val.__name__
# # list(imports())    