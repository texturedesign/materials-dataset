# Copyright (c) 2021, texture·design.

import os
import json
import pathlib
import importlib
import multiprocessing

import toml
import click

from material import Material, MaterialScanner
from library import MaterialLibrary


class MaterialExporter:
    def __init__(
        self,
        datasets: list,
        operations: list[str],
        export_path: pathlib.Path,
        export_resolution: tuple[int],
        export_format: str,
    ):
        self.datasets = datasets
        self.export_path = export_path
        self.export_resolution = export_resolution
        self.export_format = export_format
        self.ignore_default = ["\.DS_Store", "Thumbs\.db", "(?i:preview)", "(?i:thumb)"]

        self.operations = []
        for op in operations:
            mod = importlib.import_module(f"ops.{op}")
            self.operations.append(mod.process)

    def export_material(self, args):
        (filenames, info) = args

        mat = Material(filenames, **info)
        res = max(self.export_resolution) // 1024

        export_path = self.export_path / mat.hash / f"{res}K-{self.export_format.upper()}"
        if os.path.exists(export_path):
            return mat

        try:
            mat.load()
        except FileNotFoundError:
            return None

        diffuse_size = mat.images["diffuse"].shape[:2]
        if diffuse_size != self.export_resolution:
            return None

        for op in self.operations:
            op(mat)

        mat.export(export_path, format=self.export_format.lower())
        mat.unload()
        return mat

    def find_all_materials(self):
        for config in self.datasets:
            clib, cscan = config["library"], config["scanner"]
            scanner = MaterialScanner(
                exclude=self.ignore_default + cscan.get("ignore", []),
                allow_variations=False,
                allow_remaining=cscan.get("allow_remaining", []),
            )

            library = MaterialLibrary(
                clib["name"], clib["glob"], excludes=clib.get("exclude", [])
            )
            for path, info in library.find_directories():
                try:
                    for filenames in scanner.from_directory(path):
                        yield filenames, info

                except FileNotFoundError as exc:
                    print("WARNING:", path, exc)
                    continue


@click.command()
@click.argument("library-configs", nargs=-1, required=True)
@click.option("-o", "--operations", type=str, multiple=True, default=[])
@click.option("-p", "--processes", type=int, default=None)
@click.option("--export-path", type=pathlib.Path, default="cache")
@click.option("--export-resolution", type=tuple[int], default=(4096, 4096))
@click.option("--export-format", type=str, default="JPG")
def main(
    library_configs,
    operations,
    processes,
    export_path,
    export_resolution,
    export_format,
):
    libraries = [toml.load(cfg) for cfg in library_configs]

    pool = multiprocessing.Pool(processes)
    exporter = MaterialExporter(
        libraries, operations, export_path, export_resolution, export_format
    )

    index = []
    for material in pool.imap_unordered(
        exporter.export_material, exporter.find_all_materials()
    ):
        if material is None:
            continue

        data = material.extra
        data.update(
            uuid=material.hash,
            url=material.url,
            tags=list(material.tags)
        )
        index.append(data)

    json.dump(index, open(f"{export_path}/index.json", "w"))
    print(f"Exported {len(index)} materials to `{export_path}` directory.")


if __name__ == "__main__":
    main()
