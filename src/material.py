# Copyright (c) 2021, texture·design.

import os
import re
import itertools
import collections

import numpy
import torch
import base58
import imageio


def imread(filename):
    """
    Load an 8-bit or 16-bit image as a float16 tensor, output in the range [0, 255].
    """
    arr = imageio.imread(filename)
    if arr.dtype == numpy.uint16:
        arr = (arr.astype(numpy.float32) / 255.0)
    img = torch.from_numpy(arr)
    if img.ndim == 2:
        img = img.unsqueeze(-1)
    return img.to(torch.float16)


class Material:
    """
    Container for the files and data making up a PBR material.
    """

    CHANNELS = {
        "diffuse": 3,
        "normal": 3,
        # default: 1,
    }

    def __init__(self, filenames: dict, uuid=None, url: str = None, tags: set = {}):
        self.hash = base58.b58encode(uuid.bytes).decode("ascii")
        if len(self.hash) < 22:
            self.hash = '1' + self.hash
            assert base58.b58decode(self.hash).lstrip(b'\x00') == uuid.bytes.lstrip(b'\x00')

        self.url = url
        self.tags = tags
        self.filenames = filenames
        self.images = {}
        self.extra = {}

    def load(self):
        for key, filename in self.filenames.items():
            assert os.path.isfile(filename)

            img = imread(filename)

            ch = self.CHANNELS.get(key, 1)
            if ch == 3:
                if img.shape[2] == 1:
                    img = img.repeat((1, 1, 3))
                assert img.shape[2] in (3, 4), f"Expecting three channels, got {img.shape[2]}: {filename}."
                img = img[:, :, :3]
            if ch == 1:
                img = img[:, :, :3].mean(dim=2, keepdim=True)

            self.images[key] = img

    def unload(self):
        self.images = {}

    def export(self, path, format="jpg", quality=72):
        os.makedirs(path, exist_ok=True)

        for key, image in self.images.items():
            dest = os.path.join(path, f"{key}.{format}")
            imageio.imwrite(dest, image.to(torch.uint8), quality=quality)


class FileSpec:
    """
    Specification for a single file to be loaded as a material property.

    The specified `stubs` are used to match the body of the filename.
    The first item in the list is considered the `name` of the property.
    """

    def __init__(self, *stubs: list):
        self.name = stubs[0]
        self.stubs = [s if isinstance(s, tuple) else (s,) for s in stubs]


class MaterialScanner:
    """
    Creates one or more Material objects from the specified folder.
    """

    PROPERTIES = [
        FileSpec("diffuse", ("base", "color",), "color", "col", "albedo", "diff", "dif", "alb", "d"),
        FileSpec("normal", ("normal", "(open)?gl"), ("nor", "gl"), "norm", "nrm", "nor", "n"),
        FileSpec("roughness", "rough", "rou", "r"),
        FileSpec("occlusion", ("ambient", "occlusion"), "occ", "ao"),
        FileSpec("displacement", "height", "disp", "dis", "h"),
        FileSpec("bump"),
        FileSpec("metalness", "metallness", "metallic", "metal", "mtl", "m"),
        FileSpec("opacity", "alpha"),
        FileSpec("translucent", "translucency", "trans"),
        FileSpec("specular", "spec"),
        FileSpec("glossiness", "gloss"),
        FileSpec("smoothness"),
        FileSpec("reflection", "reflect"),
        FileSpec("specularLevel", ("specular", "level")),
        FileSpec("emissive", "emission"),
        FileSpec("scattering", "subsurface"),
        FileSpec("idmask", "mask", "id"),
        FileSpec("edge"),
        FileSpec("ref"),
    ]

    def __init__(
        self,
        required: set = {"diffuse", "albedo"},
        extensions: str = "(jpg|png|jpeg|bmp|tga|tif|tiff)",
        exclude: tuple = ("\.DS_Store", "Thumbs\.db", "(?i:preview)", "(?i:thumb)"),
        separators: str = "[-_ ]?",
        allow_variations=True,
        allow_remaining=[],
    ):
        self.required = required
        self.extensions = extensions
        self.exclude = exclude
        self.separators = separators
        self.allow_variations = allow_variations
        self.allow_remaining = allow_remaining

    def from_directory(self, material_path):
        """
        An iterator that builds one or more Materials from the specified directory path.
        """

        # Find all the files in the folder that aren't excluded and have the correct extension.
        prefix, files = self._scan_files(material_path)
        if len(files) == 0:
            raise FileNotFoundError(
                "MATERIAL_EMPTY_DIRECTORY", f"No image files found in directory."
            )

        # Prepare a list of regexp and sort by length: most specific files are to be matched first.
        patterns = itertools.chain(
            [(prop, p) for prop in self.PROPERTIES for p in self._make_regexp(prop)]
        )
        patterns = sorted(patterns, key=lambda p: len(p[1]), reverse=True)

        # Iterate over all the sorted patterns and load the materials one by one.
        loaded = collections.defaultdict(list)
        for prop, pattern in patterns:
            if prop.name in loaded:
                continue

            matches = self._match_regexp(files, pattern)

            # If there are multiple matches, allow variations as long as they are numbered.
            if len(matches) > 1:
                if not self.allow_variations:
                    raise FileNotFoundError(
                        "MATERIAL_NO_VARIATIONS",
                        f"Variations found for `{prop.name}` but disabled for this scanner.",
                    )

                match_prefix = os.path.commonprefix(matches)
                match_suffix = os.path.commonprefix([m[::-1] for m in matches])
                match_stub = [
                    f[len(match_prefix) :][: -len(match_suffix)] for f in matches
                ]

                if not all([s.isnumeric() for s in match_stub]):
                    raise FileNotFoundError(
                        "MATERIAL_FILE_CONFLICT",
                        f"Multiple conflicting matches found for `{prop.name}`",
                        matches,
                    )

            # Add each match to the list of variations for this material.
            for match in matches:
                filename = os.path.join(material_path, prefix + match)
                files.remove(match)
                loaded[prop.name].append(filename)

        # Check all files were found for required properties.
        for prop in self.PROPERTIES:
            if prop.name in self.required and prop.name not in loaded:
                raise FileNotFoundError(
                    "MATERIAL_FILE_MISSING",
                    f"Missing {prop.name}, remaining {len(files)}",
                    files,
                )

        # Check all images were assigned to properties.
        def _exclude(x):
            return any([re.search(a, x) for a in self.allow_remaining])

        remaining = [f for f in files if not _exclude(f)]
        if len(remaining) > 0:
            raise FileNotFoundError(
                "MATERIAL_FILE_UNKNOWN",
                f"Remaining {len(remaining)} unused files not allowed",
                remaining,
            )

        # Now return all the variations of this material in the form of an iterator.
        for keys, values in zip(
            itertools.repeat(loaded.keys()), itertools.product(*loaded.values())
        ):
            yield dict(zip(keys, values))

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

        return prefix, [f[len(prefix) :] for f in files if _include(f[len(prefix) :])]

    def _make_regexp(self, prop):
        """
        Iterator that creates all possible regular expressions for a single property.
        """
        for stub in prop.stubs:
            words = self.separators.join(stub)
            yield ".*(^|[-_ ])" + words + "([-_ ].*|[0-9]*)?" + "\." + self.extensions

    def _match_regexp(self, filenames, pattern):
        """
        Determine which subset of the files match the specified regular expression.
        """
        return [f for f in filenames if re.match(pattern, f, re.IGNORECASE) is not None]
