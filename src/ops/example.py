# Copyright (c) 2022, texture·design.

import torch


def process(mat):
    assert "diffuse" in mat.images
    assert mat.images["diffuse"].dtype == torch.float16

    # Process material in-place here.
