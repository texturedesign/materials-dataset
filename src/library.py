# Copyright (c) 2021, texture·design.

import os
import re
import glob


class MaterialLibrary:
    """
    Library of materials that's associated with a folder on disk, able to find materials from relatively
    unstructured data.
    """

    def __init__(self, path, excludes: tuple):
        self.library_path = path
        self.excludes = excludes

    def __iter__(self):
        """
        Iterator that recursively scans through all the subfolders of the library and returns
        only leaf nodes with files inside that match the specified patterns.
        """
        for path in glob.glob(self.library_path, recursive=True):
            if not os.path.isdir(path):
                continue
            if self.is_excluded(path):
                continue

            children = os.listdir(path)
            if len(children) == 0:
                continue
            if any(os.path.isdir(os.path.join(path, d)) for d in children):
                continue

            yield path

    def is_excluded(self, material_path):
        """
        Scan the list of excluded patterns and check if the current folder matches.
        """

        # Extract the path relative to the library root.
        prefix = os.path.commonpath([self.library_path, material_path])
        path = material_path[len(prefix):]

        # Check if the sub-path matches any of the regular expressions.
        for name in path.split(os.path.sep):
            if any([re.search(reject, name) is not None for reject in self.excludes]):
                return True

        return False
