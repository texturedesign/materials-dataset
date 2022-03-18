# Copyright (c) 2022, texture·design.

import os
import json
import random
import imageio
import glob
import numpy
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF

from material import Material, MaterialScanner
from library import MaterialLibrary

imageio.plugins.freeimage.download()

import random

def process(mat):
    assert "normal" in mat.images
    norm = mat.images["normal"].float()

    try:
        disp = mat.images["displacement"].float()
        with torch.no_grad():
            if disp.ndim == 3:
                disp = disp.mean(dim=2)
            disp = (disp - disp.mean()) / disp.std()
            print ('Original displacement values:', "Min:", disp.min(), 'Max', disp.max())

    except (FileNotFoundError, KeyError, ValueError):
        print('NO DISP. Skipping material.')
        return None
        # continue

    print('Normalizing displacement map for material', mat.hash)

    try:
        bump = mat.images["bump"]
    except (FileNotFoundError, KeyError, ValueError):
        print('NO BUMP')
        bump = 0

    with torch.no_grad():
        norm = (norm / 127.5 - 1)[:, :, :3]

    print(" - MIN", norm.min(0).values.min(0).values, "MAX", norm.max(0).values.max(0).values)
    print(" - MEAN", norm.mean(dim=(0,1)))
    print(" - NORM", norm.shape, '->', torch.norm(norm[:,:,:3], dim=2, p=2).mean())

    norm = TF.gaussian_blur(norm.permute(2, 0, 1), kernel_size=71, sigma=30.0)
    norm = norm.permute(1, 2, 0)

    weight = torch.tensor(
        [1 / 256, 0.001], device="cpu", dtype=torch.float32
    ).requires_grad_()

    assert disp.shape[:2] == norm.shape[:2]

    lr = 5e-4

    opt = torch.optim.Adam([weight], lr=lr)

    for i in range(15):
        opt.zero_grad()

        new_disp = disp * weight[0].abs() + bump * weight[1].abs()
        d_x = new_disp[:, 1:] - new_disp[:, :-1]
        d_x = d_x / torch.sqrt(1.0 + d_x ** 2.0)
        loss_x = F.mse_loss(d_x, norm[:, :-1, 0] * -1.0)
        loss_x.backward()
        del d_x

        new_disp = disp * weight[0].abs() + bump * weight[1].abs()
        d_y = new_disp[1:, :] - new_disp[:-1, :]
        d_y = d_y / torch.sqrt(1.0 + d_y ** 2.0)
        loss_y = F.mse_loss(d_y, norm[:-1, :, 1] * 1.0)
        loss_y.backward()
        del d_y

        print((loss_x + loss_y).item())

        del new_disp
        opt.step()

    with torch.no_grad():

        k = 32767.0 / 1.5

        # print(weight[0].abs().item(), weight[1].abs().item())
        new_disp = disp * weight[0].abs()

        print("New displacement values for material", mat.hash, "-","Min:", new_disp.min(), "Max:", new_disp.max())
        computed = 32768.0 + k * new_disp
        assert (computed >= 0).all() and (computed <= 65535).all()
        mat.images["displacement"] = computed / 255.0 # from 16-bit to 8-bit for now
        return mat
