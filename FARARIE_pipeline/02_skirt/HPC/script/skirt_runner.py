import os
import logging
import pts.simulation as sm

class SkirtRunner:
    """
    专门负责 SKIRT 模拟的配置与执行
    """
    def __init__(self, prefix, template_path, inpath, outpath):
        self.prefix = prefix                # Project Name
        self.template_path = template_path  # 原始模版路径
        self.inpath = inpath                # 存放输入txt的目录
        self.outpath = outpath              # 模拟运行和输出目录
        os.makedirs(self.outpath, exist_ok=True)

    def prepare_ski(self, seed=0, packets=1e9, weights=None):
        """
        根据模版生成特定的 .ski 文件
        weights: 字典类型，例如 {"youngstar.txt": 1.0, "agedstar.txt": 1.0}
        """
        skifile = sm.SkiFile(self.template_path)
        
        # 1. 基本配置
        skifile.setStringAttribute("//MonteCarloSimulation/random/Random", "seed", str(seed))
        skifile.setNumPrimaryPackets(packets)
        
        # 2. 预留权重接口 (默认权重为1)
        if weights:
            for filename, w in weights.items():
                xpath = f'//ParticleSource[@filename="{filename}"]'
                try:
                    skifile.setFloatAttribute(xpath, "sourceWeight", float(w))
                except Exception as e:
                    logging.warning(f"Could not set weight for {filename}: {e}")

        # 3. 保存至模拟目录
        sim_ski_path = os.path.join(self.outpath, f"{self.prefix}.ski")
        skifile.saveTo(sim_ski_path)
        logging.info(f"Saved {self.prefix}.ski")
        return sim_ski_path

    def run(self, ski_path, threads=24):
        """
        执行模拟。
        """
        logging.info(f"Executing: '{os.path.abspath(ski_path)}'...")
        skirt = sm.Skirt()
        # 单进程模拟，内部开启多线程
        skirt.execute(ski_path, 
                      inDirPath=self.inpath, 
                      outDirPath=self.outpath,
                      skiRelative=False,
                      numThreadsPerProcess=threads, 
                      numProcesses=1,
                      verbose=False, 
                      console='brief')
        logging.info("SKIRT simulation finished.")