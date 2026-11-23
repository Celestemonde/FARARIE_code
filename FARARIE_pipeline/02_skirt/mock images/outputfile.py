import os
import numpy as np
from astropy.io import fits
import h5py
from concurrent.futures import ThreadPoolExecutor
import logging

def load_sim_data(base_dir, view, data_type):
    """
    根据视角和数据类型加载 .fits 文件数据

    参数:
        base_dir: 存放 run_XX 文件夹的根目录
        view: 图像的视角（例如 'view1', 'view2' 等）
        data_type: 数据类型（'total' 或 'statsX'，如 'total', 'stats0' 等）

    返回:
        data: 6x600x600 的 NumPy 数组
    """
    folder_path = base_dir  # 文件夹路径
    
    # 文件名模板：FARARIE_viewX_data_type.fits
    # viewX 是视角，data_type 是数据类型
    # 例如，FARARIE_view1_total.fits 或 FARARIE_view1_stats0.fits
    filename = f"FARARIE_{view}_{data_type}.fits"
    file_path = os.path.join(folder_path, filename)    # 文件路径

    # 读取 .fits 文件
    with fits.open(file_path) as hdul:
        data = hdul[0].data    # 获取数据部分
    return data


def process_output(galaxy_id, base_dir, view):
    """
    加载数据、计算平均图像、R统计量和 bootstrap 百分位数图像
    base_dir: 存放 run_XX 文件夹的根目录
    view: 处理第 n 个视角
    """
    # ------------------------------
    # 平均测光图像
    # ------------------------------
    brightness_image = load_sim_data(base_dir, view, 'total')
    
    # ------------------------------
    # 计算 R 统计量
    # 联合R的方法是用这100个模拟的w1和w2的平均值
    # ------------------------------
    # N = 1e9
    W1 = load_sim_data(base_dir, view, 'stats1')
    W2 = load_sim_data(base_dir, view, 'stats2')
    W3 = load_sim_data(base_dir, view, 'stats3')
    W4 = load_sim_data(base_dir, view, 'stats4')
         
    return {
        'brightness_image': brightness_image,
        'W1': W1,
        'W2': W2,
        'W3': W3,
        'W4': W4,
    }


def process_view(id, base_dir, view):
    """
    id: 当前模拟星系的id
    base_dir: 存放 run_XX 文件夹的父目录
    view: 处理data的视角
    """
    try:
        result = process_output(id, base_dir, view)
        return view, result
    except Exception as e:
        logging.error(f"Error processing view {view}: {e}")
        return view, None
    
