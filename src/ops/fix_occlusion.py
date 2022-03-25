# Copyright (c) 2022, texture·design.


def process(mat):
    if 'occlusion' in mat.images:
        mat.images['occlusion'] += (255.0 - mat.images['occlusion'].max())
