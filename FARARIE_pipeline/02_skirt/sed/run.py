#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import getdata
from outputfile import load_sim_data
# import outputfile

import pts.simulation as sm
import pts.utils as ut
import pts.visual as vis
import pts.do

import os
import numpy as np
import multiprocessing as mp
from astropy.io import fits
import h5py
import time
import shutil


def getTNG(filepath, id, galaxyPath):
    """
    filepath: 从TNG50获取snapshot数据后，处理后的只存放必要字段数据的HDF5文件的路径
    id: 等待模拟运行的星系TNG编号
    galaxyPath: 生成SKIRT运行所需文件的存放路径
    """
    FHDUs, aged_weights = getdata.makeFHDUs(filepath, id, n1=1, n2=10)
    getdata.export_data(id, FHDUs, galaxyPath)
    
    # 源ski文件路径
    init_skipath = "/data/suminxian/FARARIE_sed/FARARIE_sed.ski"
    skifile = sm.SkiFile(init_skipath)
    
    for i, weight in enumerate(aged_weights):
        # 修改 agedstar 的权重，注意要乘以10
        skifile.setFloatAttribute(f'//ParticleSource[@filename="agedstar{i+1}.txt"]', "sourceWeight", weight * 10)
    
    sim_skipath = os.path.join(galaxyPath, 'FARARIE.ski')
    skifile.saveTo(sim_skipath)
    
    return 0


def iterate(id, seed):
    """
    id: 当前星系的ID
    seed: 随机种子，不同的任务使用不同的seed，保证每个任务内容不同
    """
    inDirPath = "/data/suminxian/FARARIE_sed/galaxy/"  
    initial_ski = os.path.join(inDirPath, "FARARIE.ski") 
    
    outDirPath = f"/data/suminxian/FARARIE_sed/simulation/run_{seed:02d}/"
    os.makedirs(outDirPath, exist_ok=True)
    
    # 生成SKI文件
    skifile = sm.SkiFile(initial_ski)
    skifile.setStringAttribute("//MonteCarloSimulation/random/Random", "seed", f"{seed}")
    sim_ski = os.path.join(outDirPath, "FARARIE.ski")
    skifile.saveTo(sim_ski)
        
    logging.info(f"Executing random seed {seed} for galaxy id {id}...")
    skirt = sm.Skirt()
    skirt.execute(sim_ski, inDirPath=inDirPath, outDirPath=outDirPath, 
                  numThreadsPerProcess=16, numProcesses=1,
                  verbose=False, console='silent')
    
    return f"Galaxy {id}, seed {seed} finished."


def process_output(galaxy_id, base_dir, view):
    """
    加载数据、计算平均图像、R统计量和 bootstrap 百分位数图像
    base_dir: 存放 run_XX 文件夹的根目录
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
    W1 = stats[:, 2]
    W2 = stats[:, 3]
    W1 = W1 ** 2  + 1e-40 # W1 的每个元素取平方， 加上1e-40
    W2 = W2 + 1e-40  # W2 的每个元素加上 1e-40
    R = np.sqrt(W2/W1 - 1/N)
    
    return {'wavelength': wavelength,
            'total_flux': total_flux,
            'R': R
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

# 初始化 PTS 库
pts.do.initializePTS()
    
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # ----------------------------
    # 配置路径和 ID
    # ----------------------------
    filepath = '/data/suminxian/TNGdata/TNG50_1.hdf5'
    galaxyPath = '/data/suminxian/FARARIE_sed/galaxy/'
    simdir = '/data/suminxian/FARARIE_sed/simulation/'
    output_dir = '/data/suminxian/FARARIE_sed/output/'
    os.makedirs(output_dir, exist_ok=True)
    output_hdf5 = os.path.join(output_dir, 'FARARIE_B105.hdf5')

    # 需要模拟的星系ID列表
    IDfile = "/data/suminxian/FARARIE_sed/GalaxyIDs/Batch_1.txt"
    IDs = list(np.loadtxt(IDfile, dtype=int)[1000:1166])

    
    for id in IDs:
        try:
            # 预处理数据
            getTNG(filepath, id, galaxyPath)
            
            logging.info(f"Starting simulation for galaxy {id}...")
            
            iterate(id, seed=1)

            # 并行处理 10 个 view
            views = [f"view{i}" for i in range(1, 11)]

            # starmap 的参数为：每个 view 调用 process_view(id, simdir, view)
            with mp.Pool(processes=10) as pool:
                sed_results = pool.starmap(process_view, [(id, simdir, view) for view in views])

            with h5py.File(output_hdf5, 'a') as hdf:
                galaxy_group = hdf.require_group(f'TNG_{id}')
                for view, result in sed_results:
                    if result is None:
                        logging.error(f"No valid result for {view} in galaxy {id}, skipping...")
                        continue
                    view_group = galaxy_group.require_group(view)
                    # 定义数据集名称与对应 key 的映射
                    datasets = {
                        "wavelength": "wavelength",
                        "total_flux": "total_flux",
                        "R": "R"
                    }
                    for ds_name, key in datasets.items():
                        # # 若数据集已存在，则先删除后创建（根据需求选择）
                        # if ds_name in view_group:
                        #     del view_group[ds_name]
                        view_group.create_dataset(ds_name, data=result[key], compression='gzip')
            logging.info(f"Finished processing galaxy {id}.")
                    
        except Exception as e:
            logging.error(f"Error in processing galaxy {id}: {e}")
        finally:
            for folder in os.listdir(simdir):
                folder_path = os.path.join(simdir, folder)
                if os.path.isdir(folder_path) and folder.startswith("run_"):
                    shutil.rmtree(folder_path)
                    logging.info(f"Deleted folder: {folder_path}")

            for filename in os.listdir(galaxyPath):
                file_path = os.path.join(galaxyPath, filename)
                if os.path.isfile(file_path) and not filename.endswith(".dat"):
                    os.remove(file_path)

