import os
import glob
import json
import random
import imageio

import numpy
import torch
import torch.nn.functional as F
import torch.optim.lr_scheduler as lr_scheduler

from material import Material, MaterialScanner
from library import MaterialLibrary

imageio.plugins.freeimage.download()

# torch.set_num_threads(1)
# DATASET_PATH = {"./allcache/*/4K-JPG/"}
# DATASET_PATH = export_path
# files = glob.glob(DATASET_PATH, recursive=True)
import random
# print (files)
# random.shuffle(files)

def normalize(export_path, material):

    for path in glob.glob(export_path, recursive=True):
        # material = path.split(os.path.sep)[-3]
        print('Normalizing displacement map for:', material)
        # try:
        disp = torch.tensor(
            imageio.imread(f"{path}/displacement.jpg").astype(numpy.float32),
            device="cpu",
        )

        with torch.no_grad():
            if disp.ndim == 3:
                disp = disp.mean(dim=2)
            disp = (disp - disp.mean()) / disp.std()
            print ('Original displacement values:', "Min:", disp.min(), 'Max', disp.max())

        init_minratio = disp.min() * - 1.0
        init_maxratio = disp.max()

        if init_minratio > init_maxratio:
            init_bias = -1
            print("Bias: Negative")
        else:
            init_bias = 1
            print("Bias: Positive")

        try:
            bump = torch.tensor(
                imageio.imread(f"{path}/bump.jpg").astype(numpy.float32),
                device="cpu",
            )
            with torch.no_grad():
                if bump.ndim == 3:
                    bump = bump.mean(dim=2)
                bump = (bump - bump.mean()) / bump.std()
        except (FileNotFoundError, KeyError, ValueError):
            print('NO BUMP')
            bump = 0


        try:
            norm = imageio.imread(f"{path}/normal.jpg")
        except ValueError as exc:
            # print('ERROR', meta_file, '-', exc)
            norm = imageio.imread(f"{path}/normal.jpg")

        if norm.dtype == numpy.uint16:
            norm = norm.astype(numpy.float32) / 256.0
            print("16-bit normal")

        else:
            norm = norm.astype(numpy.float32)

        with torch.no_grad():
            norm = torch.tensor(norm / 127.5 - 1, device="cpu")[:, :, :3]
            norm[:, :, 1] = -norm[:, :, 1]

        print(" - MIN", norm.min(0).values.min(0).values, "MAX", norm.max(0).values.max(0).values)
        print(" - MEAN", norm.mean(dim=(0,1)))
        print(" - NORM", norm.shape, '->', torch.norm(norm[:,:,:3], dim=2, p=2).mean())

        weight = torch.tensor(
            [1 / 32768, 0.001], device="cpu", dtype=torch.float32
        ).requires_grad_()

        assert disp.shape[:2] == norm.shape[:2]

        lr = 0.001

        opt = torch.optim.Adam([weight], lr=lr)

        for i in range(15):
            opt.zero_grad()
            new_disp = disp * weight[0] + bump * weight[1]
            d_x = new_disp[:, 1:] - new_disp[:, :-1]
            d_x = -d_x / torch.sqrt(1.0 + d_x ** 2.0)
            loss_x = F.mse_loss(d_x, norm[:, :-1, 0] * 1.0)
            loss_x.backward()
            del d_x

            new_disp = disp * weight[0] + bump * weight[1]
            d_y = new_disp[1:, :] - new_disp[:-1, :]
            d_y = d_y / torch.sqrt(1.0 + d_y ** 2.0)
            loss_y = F.mse_loss(d_y, norm[:-1, :, 1] * 1.0)

            loss_y.backward()
            del d_y

            print((loss_x + loss_y).item())

            del new_disp
            opt.step()


        with torch.no_grad():

            k = 32767.0 / 6

            print(weight[0].item(), weight[1].item())

            new_disp = disp * weight[0]

            #Compare new bias
            new_minratio = new_disp.min() * - 1.0
            new_maxratio = new_disp.max()

            if new_minratio > new_maxratio:
                new_bias = -1
                # print("New bias: Negative")
            else:
                new_bias = 1
                # print("New bias: Positive")

            if new_bias != init_bias:
                new_disp = -new_disp
                # print("Bias mismatch. Disp inverted!")
            else:
                new_disp = new_disp

            print("New displacement values for", material, "-","Min:", new_disp.min(), "Max:", new_disp.max())
            computed = 32768.0 + k * new_disp
            assert (computed >= 0).all() and (computed <= 65535).all()

            imageio.imwrite(
                f"{export_path}/disp_new_4k.png",
                computed.cpu().numpy().astype(numpy.uint16),
                format="PNG-FI"
            )
