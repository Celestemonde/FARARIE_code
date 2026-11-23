#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getdata
import outputfile
import logging

import pts.simulation as sm
import pts.utils as ut
import pts.visual as vis
import pts.do

from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import numpy as np
import itertools
import os
import h5py
import time
import shutil
    
    
def getTNG(filepath, id, galaxyPath):
    """
    filepath: 从TNG50获取snapshot数据后，处理后的只存放必要字段数据的HDF5文件的路径
    id: 等待模拟运行的星系TNG编号
    inDirPath: 从filepath获取星系数据加工成SKIRT运行的文件，该文件存放的文件夹路径
    
    """
    FHDUs, aged_weights = getdata.makeFHDUs(filepath, id, n1=1, n2=10)
    getdata.export_data(id, FHDUs, galaxyPath)
    
    # 源ski文件路径
    init_skipath = "/data/suminxian/SKIRT_example/data/FARARIE.ski"
    skifile = sm.SkiFile(init_skipath)
    
    for i,weight in enumerate(aged_weights):
        # 修改 agedstar 的权重，注意要乘以10
        skifile.setFloatAttribute(f'//ParticleSource[@filename="agedstar{i+1}.txt"]', "sourceWeight", weight*10)
    
    # 使用 os.path.join 将路径结合起来
    sim_skipath = os.path.join(galaxyPath, 'FARARIE.ski')
    
    skifile.saveTo(sim_skipath)
    
    return 0


def iterate(id, seed):
    """
    id: 当前星系的ID
    seed: 随机种子，不同的任务使用不同的seed，保证每个任务内容不同
    """
    inDirPath = "/data/suminxian/SKIRT_example/photon1e9/galaxy/"
    initial_ski = os.path.join(inDirPath, "FARARIE.ski") 
    
    outDirPath = f"/data/suminxian/SKIRT_example/photon1e9/simulation/"
    os.makedirs(outDirPath, exist_ok=True)
    
    # 生成SKI文件
    skifile = sm.SkiFile(initial_ski)
    skifile.setStringAttribute("//MonteCarloSimulation/random/Random", "seed", f"{seed}")
    skifile.setNumPrimaryPackets(1e9)
    sim_ski = os.path.join(outDirPath, "FARARIE.ski")
    skifile.saveTo(sim_ski)
        
    logging.info(f"Executing random seed {seed} for galaxy id {id}...")
    skirt = sm.Skirt()
    skirt.execute(sim_ski, inDirPath=inDirPath, outDirPath=outDirPath, 
                  numThreadsPerProcess=20, numProcesses=1,
                  verbose=False, console='silent')
    
    return f"Galaxy {id}, seed {seed} finished."


if __name__ == "__main__":
    
    pts.do.initializePTS()    # Initialize the PTS libraries
    
    # 从 TNG50 预处理后的数据文件的路径
    filepath = '/data/suminxian/SKIRT_example/data/TNG50_3.hdf5'
    # 单个模拟星系的文件存放路径：
    galaxyPath = '/data/suminxian/SKIRT_example/photon1e9/galaxy/'
    # 模拟过程的文件存放路径
    simdir = '/data/suminxian/SKIRT_example/photon1e9/simulation/'
    os.makedirs(simdir, exist_ok=True)
    # 最终产品输出的文件夹路径
    output_dir = '/data/suminxian/SKIRT_example/photon1e9/output/'
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    # 储存所有模拟后结果的HDF5文件的路径
    output_hdf5 = os.path.join(output_dir, 'Sub455291.hdf5')
    
    # 需要模拟的星系的id
    # IDfile = "/data/suminxian/FARARIE_1e7/GalaxyIDs/Batch_3.txt"
    # IDs = list(np.loadtxt(IDfile, dtype=int)[:])
    IDs = [455291,]
    
    for id in IDs:
        
        # getTNG(filepath, id, galaxyPath)
        seed = 1
        # result = iterate(id, seed)
        # logging.info(result)
        
        with mp.Pool(processes=10) as pool:
            views = [f"view{i}" for i in range(1, 11)]
            args = [(id, simdir, view) for view in views]
            
            results = pool.starmap(outputfile.process_view, args)
                
            with h5py.File(output_hdf5, 'a') as hdf:
                galaxy_group = hdf.require_group(f'TNG_{id}')
                for view, result in results:
                    view_group = galaxy_group.require_group(view)

                    datasets = {
                        "Image": "brightness_image",
                        "W1": "W1",
                        "W2": "W2",
                        "W3": "W3",
                        "W4": "W4",
                    }

                    for group_name, result_key in datasets.items():
                        group = view_group.require_group(group_name)
                        for i, band in enumerate(['u', 'g', 'r', 'i', 'z']):
                            group.create_dataset(f'{band}_band',
                                                 data=result[result_key][i],
                                                 compression='gzip')
        
        shutil.rmtree(simdir)
        logging.info(f"Deleted folder: {simdir}")
                
        for filename in os.listdir(galaxyPath):
            file_path = os.path.join(galaxyPath, filename)
            if os.path.isfile(file_path) and not filename.endswith(".dat"):
                os.remove(file_path)