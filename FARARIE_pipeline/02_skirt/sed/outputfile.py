import os
import numpy as np
from astropy.io import fits
import h5py
from concurrent.futures import ThreadPoolExecutor


def load_sim_data(base_dir, view, data_type):
    """
    根据视角和数据类型加载 .dat 文件数据

    参数:
        base_dir: 存放 run_XX 文件夹的根目录
        view: 图像的视角（例如 'view1', 'view2' 等）
        data_type: 数据类型（'sed' 或 'sedstats'）

    返回:
        data:
    """
    # 一个run_01文件夹
    folder_name = "run_01"
    folder_path = os.path.join(base_dir, folder_name)  # 文件夹路径
    
    # 文件名模板：FARARIE_viewX_data_type.dat
    # viewX 是视角，data_type 是数据类型
    # 例如，FARARIE_view1_sed.dat 或 FARARIE_view1_sedstats.dat
    filename = f"FARARIE_{view}_{data_type}.dat"
    file_path = os.path.join(folder_path, filename)  # 文件路径

    # 读取 .dat 文件, 使用 np.loadtxt 读取数值数据（np.loadtxt 默认会忽略以 '#' 开头的行）
    data = np.loadtxt(file_path, dtype=np.float64)
        
    return data


def save_to_hdf5(galaxy_id, base_dir, view, hdf):
    """
    将平均图像保存到 HDF5 文件中，并波段命名
    """
    
    # ------------------------------
    # SED
    # ------------------------------
    sed_data = load_sim_data(base_dir, view, 'sed')
    wavelength = sed_data[:, 0]   # lambda (micron)
    total_flux = sed_data[:, 1]   # F_nu (Jy)
    
    # ------------------------------
    # 计算 R 统计量
    # ------------------------------
    N = 1e7
    stats = load_sim_data(base_dir, view, 'sedstats')
    W1 = stats[:, 1]
    W2 = stats[:, 2]
    W1 = W1 ** 2  + 1e-40 # W1 的每个元素取平方， 加上1e-40
    W2 = W2 + 1e-40  # W2 的每个元素加上 1e-40
    R = np.sqrt(W2/W1 - 1/N)
        
    # 存储数据到 hdf5
    galaxy_group = hdf.require_group(f'{galaxy_id}')
    view_group = galaxy_group.require_group(view)
    
    view_group.create_dataset('wavelength', data=wavelength, compression='gzip')
    view_group.create_dataset('total flux', data=total_flux, compression='gzip')
    view_group.create_dataset('R', data=R, compression='gzip')
    
    # sed_group = view_group.require_group('SED')
    # R_group = view_group.require_group('R')
#     sed_group.create_dataset('wavelength', data=wavelength, compression='gzip')
#     sed_group.create_dataset('total flux', data=total_flux, compression='gzip')
#     R_group.create_dataset('wavelength', data=wavelength, compression='gzip')
#     R_group.create_dataset('R', data=R, compression='gzip')
        
        
def main(filepath, galaxy_id, base_dir, view):
    with h5py.File(filepath, 'a') as hdf:
        save_to_hdf5(galaxy_id, base_dir, view, hdf)