# Copyright (c) 2021, texture·design.

import os
import re
import glob
import uuid


class MaterialLibrary:
    """
    Library of materials that's associated with a folder on disk, able to find materials from relatively
    unstructured data.
    """

    def __init__(self, name, path, excludes: list = [], stopwords: str = "(jpg|png)"):
        self.name = name
        self.root = path
        self.excludes = excludes
        self.stopwords = stopwords

    def __iter__(self):
        """
        Iterator that recursively scans through all the subfolders of the library and returns
        only leaf nodes with files inside that match the specified patterns.
        """
        for path in glob.glob(self.root, recursive=True):
            if not os.path.isdir(path):
                continue
            if self.is_excluded(path):
                continue

            children = os.listdir(path)
            if len(children) == 0:
                continue
            if any(os.path.isdir(os.path.join(path, d)) for d in children):
                continue

            info = self.extract_info(path)
            yield path, info

    def extract_info(self, material_path):
        """
        Determine meta-data such as material url, unique ID, and the tags based on a path.
        """
        common_path = os.path.commonpath([material_path, self.root])
        path = material_path[len(common_path) + 1 :]
        mat_tags = self.split_words(path)

        name = path.split(os.path.sep)[0]
        mat_url = f"https://{self.name}/a/{name}"
        mat_id = uuid.uuid5(uuid.NAMESPACE_URL, mat_url)
        return dict(uuid=mat_id, url=mat_url, tags=mat_tags)

    def split_words(self, path):
        """
        Extract unique tags from a path by splitting out words with a regular expression.
        """
        re_words = re.compile(
            r"""
            [A-Z]+(?=[A-Z][a-z]) |  # Uppercase before capitalized word
            [A-Z]?[a-z]+ |          # Capitalized words
            [A-Z]+ |                # All uppercase words
            \d+[A-Za-z]* |          # Mixed identifiers
            \d+                     # Numbers
        """,
            re.VERBOSE,
        )

        def _exclude(w):
            if w[0].isnumeric():
                return True
            return re.match(self.stopwords, w, re.IGNORECASE)

        return {w.lower() for w in set(re_words.findall(path)) if not _exclude(w)}

    def is_excluded(self, material_path):
        """
        Scan the list of excluded patterns and check if the current folder matches.
        """

        # Extract the path relative to the library root.
        prefix = os.path.commonpath([self.root, material_path])
        path = material_path[len(prefix) :]

        # Check if the sub-path matches any of the regular expressions.
        for name in path.split(os.path.sep):
            if any([re.search(reject, name) is not None for reject in self.excludes]):
                return True

        return False
