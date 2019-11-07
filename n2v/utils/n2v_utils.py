import numpy as np
from tqdm import tqdm
from ..internals.N2V_DataWrapper import N2V_DataWrapper as dw


def get_subpatch(patch, coord, local_sub_patch_radius):
    start = np.maximum(0, np.array(coord) - local_sub_patch_radius)
    end = start + local_sub_patch_radius*2 + 1

    start = np.append(start, 0)
    end = np.append(end, patch.shape[-1])

    shift = np.minimum(0, patch.shape - end)

    start += shift
    end += shift

    slices = [ slice(s, e) for s, e in zip(start, end)]

    return patch[tuple(slices)]


def random_neighbor(shape, coord):
    rand_coords = sample_coords(shape, coord)
    while np.any(rand_coords == coord):
        rand_coords = sample_coords(shape, coord)

    return rand_coords


def sample_coords(shape, coord, sigma=4):
    return [normal_int(c, sigma, s) for c, s in zip(coord, shape)]


def normal_int(mean, sigma, w):
    return int(np.clip(np.round(np.random.normal(mean, sigma)), 0, w - 1))


def pm_normal_withoutCP(local_sub_patch_radius):
    def normal_withoutCP(patch, coord, dims):
        rand_coords = random_neighbor(patch.shape, coord)
        return patch[tuple(rand_coords)]
    return normal_withoutCP


def pm_uniform_withCP(local_sub_patch_radius):
    def random_neighbor_withCP_uniform(patch, coord, dims):
        sub_patch = get_subpatch(patch, coord,local_sub_patch_radius)
        rand_coords = [np.random.randint(0, s) for s in sub_patch.shape[0:dims]]
        return sub_patch[tuple(rand_coords)]
    return random_neighbor_withCP_uniform


def pm_normal_additive(pixel_gauss_sigma):
    def pixel_gauss(patch, coord, dims):
        return np.random.normal(patch[tuple(coord)], pixel_gauss_sigma)
    return pixel_gauss


def pm_normal_fitted(local_sub_patch_radius):
    def local_gaussian(patch, coord, dims):
        sub_patch = get_subpatch(patch, coord, local_sub_patch_radius)
        axis = tuple(range(dims))
        return np.random.normal(np.mean(sub_patch, axis=axis), np.std(sub_patch, axis=axis))
    return local_gaussian


def pm_identity(local_sub_patch_radius):
    def identity(patch, coord, dims):
        return patch[tuple(coord)]
    return identity


def manipulate_val_data(X_val, Y_val, perc_pix=0.198, shape=(64, 64), value_manipulation=pm_uniform_withCP(5)):
    dims = len(shape)
    if dims == 2:
        box_size = np.round(np.sqrt(100/perc_pix)).astype(np.int)
        get_stratified_coords = dw.__get_stratified_coords2D__
        rand_float = dw.__rand_float_coords2D__(box_size)
    elif dims == 3:
        box_size = np.round(np.sqrt(100/perc_pix)).astype(np.int)
        get_stratified_coords = dw.__get_stratified_coords3D__
        rand_float = dw.__rand_float_coords3D__(box_size)

    n_chan = X_val.shape[-1]

    Y_val *= 0
    for j in tqdm(range(X_val.shape[0]), desc='Preparing validation data: '):
        coords = get_stratified_coords(rand_float, box_size=box_size,
                                            shape=np.array(X_val.shape)[1:-1])
        for c in range(n_chan):
            indexing = (j,) + coords + (c,)
            indexing_mask = (j,) + coords + (c + n_chan,)
            y_val = X_val[indexing]
            x_val = value_manipulation(X_val[j, ..., c], coords, dims)

            Y_val[indexing] = y_val
            Y_val[indexing_mask] = 1
            X_val[indexing] = x_val
