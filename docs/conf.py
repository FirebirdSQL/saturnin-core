# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import sphinx_bootstrap_theme
from saturnin.core.__about__ import __version__

# -- Project information -----------------------------------------------------

project = 'saturnin-core'
copyright = '2019-present, The Firebird Project'
author = 'Pavel Císař'

# The short X.Y version
version = __version__

# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.intersphinx',
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    #'sphinx_autodoc_typehints',
    'sphinx.ext.autosectionlabel',
    'sphinx.ext.todo',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', 'requirements.txt']

default_role = 'py:obj'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'

html_theme = "bootstrap"
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()

# bootstrap theme config

# (Optional) Logo. Should be small enough to fit the navbar (ideally 24x24).
# Path should be relative to the ``_static`` files directory.
#html_logo = "my_logo.png"

# Theme options are theme-specific and customize the look and feel of a
# theme further.
html_theme_options = {
    # Navigation bar title. (Default: ``project`` value)
    #'navbar_title': "Saturnin CORE",

    # Tab name for entire site. (Default: "Site")
    'navbar_site_name': "Content",

    # A list of tuples containing pages or urls to link to.
    # Valid tuples should be in the following forms:
    #    (name, page)                 # a link to a page
    #    (name, "/aa/bb", 1)          # a link to an arbitrary relative url
    #    (name, "http://example.com", True) # arbitrary absolute url
    # Note the "1" or "True" value above as the third argument to indicate
    # an arbitrary url.
    'navbar_links': [
        ("Usage Guide", "usage-guide"),
        ("Services", "services"),
        ("Protocol buffers", "protobuf"),
        #("Modules", "py-modindex"),
        #("Index", "genindex"),
    ],

    # Render the next and previous page links in navbar. (Default: true)
    'navbar_sidebarrel': False,

    # Render the current pages TOC in the navbar. (Default: true)
    #'navbar_pagenav': True,

    # Tab name for the current pages TOC. (Default: "Page")
    #'navbar_pagenav_name': "Page",

    # Global TOC depth for "site" navbar tab. (Default: 1)
    # Switching to -1 shows all levels.
    'globaltoc_depth': 3,

    # Include hidden TOCs in Site navbar?
    #
    # Note: If this is "false", you cannot have mixed ``:hidden:`` and
    # non-hidden ``toctree`` directives in the same page, or else the build
    # will break.
    #
    # Values: "true" (default) or "false"
    'globaltoc_includehidden': "true",

    # HTML navbar class (Default: "navbar") to attach to <div> element.
    # For black navbar, do "navbar navbar-inverse"
    'navbar_class': "navbar navbar-inverse",

    # Fix navigation bar to top of page?
    # Values: "true" (default) or "false"
    'navbar_fixed_top': "true",

    # Location of link to source.
    # Options are "nav" (default), "footer" or anything else to exclude.
    'source_link_position': "none",

    # Bootswatch (http://bootswatch.com/) theme.
    #
    # Options are nothing (default) or the name of a valid theme
    # such as "cosmo" or "sandstone".
    #
    # The set of valid themes depend on the version of Bootstrap
    # that's used (the next config option).
    #
    # Currently, the supported themes are:
    # - Bootstrap 2: https://bootswatch.com/2
    # - Bootstrap 3: https://bootswatch.com/3
    #'bootswatch_theme': "united", # cerulean, flatly, lumen, materia, united, yeti
    'bootswatch_theme': "cerulean",

    # Choose Bootstrap version.
    # Values: "3" (default) or "2" (in quotes)
    'bootstrap_version': "2",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# -- Extension configuration -------------------------------------------------

autosectionlabel_prefix_document = True

# Autodoc options
# ---------------
autodoc_default_options = {
    'content': 'both',
    'members': True,
    'member-order': 'groupwise',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'no-inherited-members': True,
    'no-private-members': True,
}
set_type_checking_flag = True
autodoc_class_signature = 'mixed'
always_document_param_types = True
autodoc_typehints = 'both' # default 'signature'
autodoc_typehints_format = 'short'
autodoc_typehints_description_target = 'all'

autodoc_type_aliases = {'TSupplement': '~saturnin.base.types.TSupplement',
                        'Token': '~saturnin.base.types.Token',
                        'RoutingID': '~saturnin.base.types.RoutingID',
                        'TZMQMessage': '~saturnin.base.transport.TZMQMessage',
                        'TMessageFactory': '~saturnin.base.transport.TMessageFactory',
                        'TSocketOptions': '~saturnin.base.transport.TSocketOptions',
                        'TMessageHandler': '~saturnin.base.transport.TMessageHandler',
                        }

#typehints_fully_qualified = False

# Napoleon options
# ----------------
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_rtype = True
napoleon_use_param = True
napoleon_use_keyword = True
napoleon_attr_annotations = True
napoleon_preprocess_types = True

#napoleon_type_aliases = {'TSupplement': '~saturnin.base.types.TSupplement',
                         #'Token': '~saturnin.base.types.Token',
                         #'RoutingID': '~saturnin.base.types.RoutingID',
                         #'TZMQMessage': '~saturnin.base.transport.TZMQMessage',
                         #'TMessageFactory': '~saturnin.base.transport.TMessageFactory',
                         #'TSocketOptions': '~saturnin.base.transport.TSocketOptions',
                         #'TMessageHandler': '~saturnin.base.transport.TMessageHandler',
                         #}

# -- Options for intersphinx extension ---------------------------------------

# intersphinx
intersphinx_mapping = {'python': ('https://docs.python.org/3', None),
                       'base': ('https://firebird-base.readthedocs.io/en/latest', None),
                       'pyzmq': ('https://pyzmq.readthedocs.io/en/latest/', None),
                       'rich': ('https://rich.readthedocs.io/en/latest/', None),
                       'saturnin': ('https://saturnin.readthedocs.io/en/latest/', None),
                       }

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
