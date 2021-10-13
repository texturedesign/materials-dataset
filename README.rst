Materials Dataset
=================

A python script to create a dataset of PBR materials (SVBRDF) from CC0 sources online.

Sources
-------

The script should work with many different sources of materials.  It officially supports the following:

* `AmbientCG <https://ambientcg.com/>`_ — Subscribe to Patreon for cloud drive access.
* `PolyHaven <https://polyhaven.com/>`_ — For drive access, also subscribe to Patreon.

NOTE: Once you have downloaded the files, you may need to manually rename a few of them if there are warnings or errors.


Scripts
-------

To create the dataset from the sources you downloaded, run the following scripts with `Python 3.x <https://www.python.org/downloads/>`_ installed.  `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ is the recommended way to get up and running if you don't have it setup already.

.. code:: bash

    # Create a dataset out of all sources.
    python src/main.py config/*.toml

    # Create a dataset from one source in specific directory.
    python src/main.py config/ambientcg.toml --export-path ./output/ --export-format PNG

The albedo files are expected to be stored with an sRGB color profile.  The roughness, occlusion, and normals store raw linear values.  The normals are in OpenGL format.


Configuration
-------------

Here is an example configuration file for the data sources:

.. code:: toml

    [library]
    name = "ambientcg.com"
    glob = "/home/user/ambientcg.com/*/4K-JPG"
    exclude = [
        '^Manhole',
        '^TreeEnd',
    ]

    [scanner]
    ignore = []
    allow_remaining = [
        'NormalDX'
    ]

A short description of what these options do:

* The ``ignore`` option is a list of files that should not be used when scanning for images to use in the material, for example preview renderings.

* The ``exclude`` option is a lists of regular expressions to filter out paths in the dataset.  In this case, we want to avoid manhule covers and tree stumps since they are objects and not seamless textures.

* The ``allow_remaining`` option is also a list of regular expressions to make sure any leftover files that were not recognized by the material scanner are flagged for manual inspection.
