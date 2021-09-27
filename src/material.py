# Copyright (c) 2021, texture·design.

import os
import re

import itertools
import collections



class Material:
    """
    Container for the files and data making up a PBR material.
    """

    def __init__(self, filenames: dict):
        assert type(filenames) == dict
        self.filenames = filenames

    def load(self):
        raise NotImplementedError


class FileSpec:
    """
    Specification for a single file to be loaded as a material property.

    The specified `stubs` are used to match the body of the filename.
    The first item in the list is considered the `name` of the property.
    """

    def __init__(self, *stubs : list):
        self.name = stubs[0]
        self.stubs = [s if isinstance(s, tuple) else (s,) for s in stubs]


class MaterialBuilder:
    """
    Creates one or more Material objects from the specified folder.
    """

    PROPERTIES = [
        FileSpec('diffuse', ('base', 'color',), 'color', 'col', 'albedo', 'diff', 'dif', 'alb', 'd'),
        FileSpec('normal', ('normal', 'gl'), ('nor', 'gl'), 'norm', 'nrm', 'nor', 'n'),
        FileSpec('roughness', 'rough', 'rou', 'r'),
        FileSpec('occlusion', ('ambient', 'occlusion'), 'occ', 'ao'),
        FileSpec('displacement', 'height', 'disp', 'dis', 'h'),
        FileSpec('bump'),
        FileSpec('metalness', 'metallness', 'metallic', 'metal', 'mtl', 'm'),
        FileSpec('opacity', 'translucent'),
        FileSpec('specular', 'spec'),
        FileSpec('glossiness', 'gloss'),
        FileSpec('smoothness'),
        FileSpec('reflection', 'reflect'),
        FileSpec('specularLevel', ('specular', 'level')),
        FileSpec('emissive', 'emission'),
        FileSpec('scattering', 'subsurface'),
        FileSpec('idmask', 'id'),
        FileSpec('edge'),
        FileSpec('arm'),
        FileSpec('ref'),
    ]

    def __init__(self,
        required: set = {'diffuse', 'albedo'},
        extensions: str = '(jpg|png|jpeg|bmp|tga|tif|tiff)',
        exclude: tuple = ('.DS_Store', 'Thumbs.db', '(?i:preview)', '(?i:thumb)'),
        separators: str = '[-_ ]?'
    ):
        self.required = required
        self.extensions = extensions
        self.exclude = exclude
        self.separators = separators

    def from_files(self, material_path):
        """
        An iterator that builds one or more Materials from the specified path.
        """

        # Find all the files in the folder that aren't excluded and have the correct extension.
        prefix, files = self._scan_files(material_path)
        if len(files) == 0:
            raise FileNotFoundError("MATERIAL_EMPTY_DIRECTORY", f"No image files found in directory.")

        # Prepare a list of regexp and sort by length: most specific files are to be matched first.
        patterns = itertools.chain([(prop, p) for prop in self.PROPERTIES for p in self._make_regexp(prop)])
        patterns = sorted(patterns, key=lambda p: len(p[1]), reverse=True)

        # Iterate over all the sorted patterns and load the materials one by one.
        loaded = collections.defaultdict(list)
        for prop, pattern in patterns:
            if prop.name in loaded:
                continue

            matches = self._match_regexp(files, pattern)

            # If there are multiple matches, allow variations as long as they are numbered.
            if len(matches) > 1:
                match_prefix = os.path.commonprefix(matches)
                match_suffix = os.path.commonprefix([m[::-1] for m in matches])
                match_stub = [f[len(match_prefix):][:-len(match_suffix)] for f in matches]

                if not all([s.isnumeric() for s in match_stub]):
                    raise FileNotFoundError("MATERIAL_FILE_CONFLICT", f"Multiple conflicting matches found for `{prop.name}`", matches)

            # Add each match to the list of variations for this material.
            for match in matches:
                filename = os.path.join(material_path, prefix + match)
                files.remove(match)
                loaded[prop.name].append(filename)

        # Check all files were found for required properties.
        for prop in self.PROPERTIES:
            if prop.name in self.required and prop.name not in loaded:
                raise FileNotFoundError("MATERIAL_FILE_MISSING", f"Missing {prop.name}, remaining {len(files)}", files)

        # Now return all the variations of this material in the form of an iterator.
        for keys, values in zip(itertools.repeat(loaded.keys()), itertools.product(*loaded.values())):
            yield Material(dict(zip(keys, values)))

    def _scan_files(self, material_path):
        """
        Load all the files in a specified path that aren't excluded and have the correct extension.
        """
        def _exclude(x):
            return any([re.search(excl, x) for excl in self.exclude])

        files = [f for f in os.listdir(material_path) if not _exclude(f)]
        prefix = os.path.commonprefix(files)

        def _include(x):
            return re.match("(.+)" + self.extensions, x, flags=re.IGNORECASE)
        return prefix, [f[len(prefix):] for f in files if _include(f[len(prefix):])]

    def _make_regexp(self, prop):
        """
        Iterator that creates all possible regular expressions for a single property.
        """
        for stub in prop.stubs:
            yield '.*(^|[-_ ])' + self.separators.join(stub) + '([-_ ].*|[0-9]*)?' + '\.' + self.extensions

    def _match_regexp(self, filenames, pattern):
        """
        Determine which subset of the files match the specified regular expression.
        """
        return [f for f in filenames if re.match(pattern, f, re.IGNORECASE) is not None]
