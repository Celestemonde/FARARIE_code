import os
import sys
import logging
import traceback
import pts.simulation as sm
import numpy as np
import gc
import shutil

from data_builder import SubhaloDataExporter
from skirt_runner import SkirtRunner
from post_processor import PostProcessor


def process_single_galaxy(subhalo_id, config):
    """
    执行单个星系模拟的完整流程
    """
    logging.info(f"========== Starting Pipeline for Subhalo {subhalo_id} ==========")
    
    inpath = config["INPUT_DIR"] if config["INPUT_DIR"] is not None else os.path.join(config["BASE_WORK_DIR"], "SKIRT_input")
    outpath = config["OUTPUT_DIR"] if config["OUTPUT_DIR"] is not None else os.path.join(config["BASE_WORK_DIR"], "SKIRT_output")
    
    try:
        # ---------------------------------------------------------
        # Step 1: Data Building (提取模拟数据输出至 .txt 文件)
        # ---------------------------------------------------------
        logging.info("[Step 1] Building input data...")
        exporter = SubhaloDataExporter(config["SOURCE_HDF5_PATH"])
        exporter.export_galaxy(subhalo_id, inpath)

        # ---------------------------------------------------------
        # Option： 当需要从外部导入滤波片时取消注释以下部分
        # ---------------------------------------------------------
        filters = ["u", "g", "r", "i", "z"]
        for f in filters:
            filename = f"{f}_transmission.txt"
            shutil.copy(os.path.join("/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/raw_data/", filename), inpath)
        
        # ---------------------------------------------------------
        # Step 2: SKIRT Simulation (生成 ski 并运行)
        # ---------------------------------------------------------
        logging.info("[Step 2] Running SKIRT simulation...")
        runner = SkirtRunner(
            prefix=config["PREFIX"], 
            template_path=config["TEMPLATE_SKI_PATH"], 
            inpath=inpath, 
            outpath=outpath
        )

        # 可用 subhalo_id 作为随机种子，保证结果可复现
        ski_path = runner.prepare_ski(seed=config["SEED"] if config["SEED"] is not None else subhalo_id, 
                                      packets=config["PHOTON_PACKET"] if config["PHOTON_PACKET"] is not None else 1e9)
        runner.run(ski_path, threads=config["SKIRT_THREADS"])
        
        # ---------------------------------------------------------
        # Step 3: Post Processing (解析 FITS 并写入 HDF5)
        # ---------------------------------------------------------
        logging.info("[Step 3] Post-processing FITS to HDF5...")
        
        # 在主进程安全地使用 pts 获取视角信息
        simulation = sm.createSimulation(outDirPath=outpath, prefix=config["PREFIX"])
        view_names = [inst.name() for inst in simulation.instruments()]
        
        if not view_names:
            logging.error(f"No views found for {subhalo_id}. SKIRT might have failed.")
            return False
            
        processor = PostProcessor(subhalo_id, outpath=outpath, result_path=config["RESULT_PATH"], outmode=config["OUTMODE"])
        processor.process_all_views(
            prefix=config["PREFIX"], 
            view_names=view_names, 
            max_workers=config["POST_PROCESS_WORKERS"]
        )
        
        logging.info(f"========== Pipeline completed for {subhalo_id} ==========\n")
        return True
        
    except Exception as e:
        logging.error(f"Pipeline failed for {subhalo_id}: {e}")
        logging.error(traceback.format_exc())
        return False

    
def main(target_galaxies, config):
    # 配置日志格式
    # for handler in logging.root.handlers[:]:
    #     logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # 目标星系列表 (可以从文件读取，或者传入一个 array)
    if not isinstance(target_galaxies, (list, tuple, np.ndarray)):
        target_galaxies = [target_galaxies]
    
    success_count = 0
    for sid in target_galaxies:
        config_sp = config.copy()
        work_dir = os.path.join(os.path.abspath(config["BASE_WORK_DIR"]), str(sid))
        config_sp["BASE_WORK_DIR"] = work_dir

        try:
            success = process_single_galaxy(sid, config_sp)
            if success:
                success_count += 1
        finally:
            # 2. 无论是否成功，只要目录存在且不是当前目录，就清理
            if os.path.exists(work_dir):
                logging.info(f"Cleaning up work directory: {work_dir}")
                shutil.rmtree(work_dir)
            
            del config_sp
            gc.collect()
            
    logging.info(f"All tasks finished. Success rate: {success_count}/{len(target_galaxies)}")
    

def get_default_config():
    """提供默认配置，方便使用时 Jupyter 直接调用"""
    return {
        'PREFIX': 'test',
        'TEMPLATE_SKI_PATH': None,
        'SOURCE_HDF5_PATH': None,
        'RESULT_PATH': './',
        'OUTMODE':'single',  # mode can be selected only between 'single' and 'batch'
        
        'BASE_WORK_DIR': './run',
        'INPUT_DIR': None,
        'OUTPUT_DIR': None,
        
        'SKIRT_THREADS': 24,
        'POST_PROCESS_WORKERS': 2,  # 处理 Instrument 结果输出时的进程数
        'PHOTON_PACKET': 1e9,
        'SEED': 0,
    }


if __name__ == "__main__":
    import argparse
    
    # ArgumentParser() 的作用
    # 创建一个解析器对象，后续所有 add_argument 都挂在它上面。description 是运行 -h 时显示的说明文字
    parser = argparse.ArgumentParser(description="MCRT main.py Receives Several Para for Configration")

    parser.add_argument("-g", "--galaxy_id",  type=int,   required=True,  metavar="ID",     help="Galaxy ID to be simulated")
    parser.add_argument("-f", "--hfile",      type=str,   required=True,  metavar="PATH",   help="HDF5 file of TNG particle data")
    parser.add_argument("-k", "--skipath",    type=str,   required=True,  metavar="PATH",   help="Path to the main ski file")
    parser.add_argument("-m", "--mode",       type=str,   default="single", metavar="MODE", help="Results output mode('single' or 'batch')")
    
    parser.add_argument("-p", "--prefix",     type=str,   default="test", metavar="NAME",   help="Ski file prefix (simulation project name)")
    parser.add_argument("-o", "--resultpath", type=str,   default="./",   metavar="PATH",   help="Output directory for simulation results")
    
    parser.add_argument("-n", "--photons",    type=float, default=1e9,    metavar="N",      help="Number of photon packets")
    parser.add_argument("-S", "--seed",       type=int,   default=0,      metavar="N",      help="Random seed")
    parser.add_argument("-t", "--thread",     type=int,   default=24,     metavar="N",      help="Threads per simulation")
    parser.add_argument("-w", "--worker",     type=int,   default=2,      metavar="N",      help="Parallel worker processes for post-processing")

    args = parser.parse_args()

    config = {
        'PREFIX': args.prefix,
        'TEMPLATE_SKI_PATH': args.skipath,
        'SOURCE_HDF5_PATH': args.hfile,
        'RESULT_PATH': args.resultpath,
        'OUTMODE': args.mode,

        'BASE_WORK_DIR': "/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/run",
        'INPUT_DIR': None,
        'OUTPUT_DIR': None,

        'SKIRT_THREADS': args.thread,
        'POST_PROCESS_WORKERS': args.worker,  # 输出结果时的进程数，一般使用等于视角数的进程数
        'PHOTON_PACKET': args.photons,
        'SEED': args.seed,
    }
    
    target_galaxies = args.galaxy_id
    main(target_galaxies, config)