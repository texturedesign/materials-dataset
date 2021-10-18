Materials Dataset
=================

A python script to create a dataset of PBR materials (SVBRDF) from CC0 sources online.

Sources
-------

The script should work with many different sources of materials.  It officially supports `AmbientCG <https://ambientcg.com/>`_ and `PolyHaven <https://polyhaven.com/>`_ as sources.  There are multiple ways you can get access to the data:

1. Browse materials manually from the websites and extract the images into the ``#/data/<source>/<format>/<material>/`` folder.  The script uses a format that's ``JPG`` with a resolution of ``4K`` by default.
2. Subscribe to the project via Patreon for cloud drive access, add a symlink in ``#/data/<source>``.  If you don't set filters, you'll get all formats and resolutions!  (See their help for setting filters.)
3. Download the `sample .zip files <https://github.com/texturedesign/materials-dataset/releases/tag/v0.0>`_ and extract the archives inside the ``#/data/`` folder.  By default, the samples are highly compressed ``JPG`` at ``4K`` resolution.
 
In all three cases, you should end up with image files (e.g. ``*.png`` or ``*.jpg``) three or four levels deep within the directory structure, for example ``#/data/polyhaven.com/4k/asphalt_02`` .  If you download the full drive content, you may need to manually rename a few of them (for specific textures only) if there are warnings or errors.


Scripts
-------

To create the dataset from the sources you downloaded, run the following scripts with `Python 3.x <https://www.python.org/downloads/>`_ installed.  `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ is the recommended way to get up and running if you don't have it setup already.  Then you can run the scripts in this repository:

.. code:: bash

    # Create a dataset out of all sources.
    python src/main.py config/*.toml

    # Create a dataset from one source in specific directory.
    python src/main.py config/ambientcg.toml --export-path ./output/ --export-format PNG

If this works, with the sample data provided above, you should see the following output:

.. code:: bash

    Exported 14 materials to `cache` directory.

There you'll find multiple sub-folders corresponding to UUID of each material.  The albedo files are expected to be stored with an sRGB color profile.  The roughness, occlusion, and normals store raw linear values.  The normals are in OpenGL format.


Configuration
-------------

Here is an example configuration file for the data sources:

.. code:: toml

    [library]
    name = "ambientcg.com"
    glob = "./data/ambientcg.com/*/4K-JPG"
    exclude = [
        '^Manhole',
        '^TreeEnd',
    ]

    [scanner]
    ignore = []
    allow_remaining = [
        '^NormalDX'
    ]

A short description of what these options do:

* The ``exclude`` option is a lists of regular expressions to filter out paths in the dataset.  In this case, we want to avoid manhole covers and tree stumps since they are objects and not seamless textures.

* The ``ignore`` option is a list of regular expressions matching files that should not be used when scanning for images to use in the material, for example preview renderings.

* The ``allow_remaining`` option is also a list of regular expressions to make sure any leftover files that were not recognized by the material scanner are flagged for manual inspection.


Roadmap
-------

At the high-level, we're planning in this direction:

1. **Standardization** — Ensuring all materials are consistent and with standardized units, in particular for the displacement maps.  Adding tests to catch possible problems with new content.
2. **Annotation** — Manually labeling the materials (e.g. procedural, scan-based), tagging the content (e.g. rock / gravel / sand), adding metrics (e.g. area size), and adding full descriptions.
3. **Augmentation** — Creating new materials and annotations from existing ones in the dataset to help cover new parts of the design space, using a combination of algorithms and human expertise.

For the short-term, see the `project Issues <https://github.com/texturedesign/materials-dataset/issues>`_ for tasks that are in progress or discussion.
