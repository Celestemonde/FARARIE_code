import h5py
import numpy as np
import os
import logging
import gc

class SubhaloDataExporter:
    def __init__(self, h5_path):
        self.h5_path = h5_path
        
        self.headers = {
            "dust":"\n".join([
                "import file for Voronoi mesh media -- dust(TNG50 run)",
                "Column 1: position x (kpc)",
                "Column 2: position y (kpc)",
                "Column 3: position z (kpc)",
                "Column 4: dust mass density (Msun/pc3)",
                "Column 5: metallicity (1)",
                "Column 6: temperature (K)",
                "Column 7: velocity vx (km/s)",
                "Column 8: velocity vy (km/s)",
                "Column 9: velocity vz (km/s)",
                " " # 空注释行
            ]),
            "young": "\n".join([
                "import file for particle source -- young star(TNG50 run)",
                "Column 1: position x (kpc)",
                "Column 2: position y (kpc)",
                "Column 3: position z (kpc)",
                "Column 4: smoothing length (kpc)",
                "Column 5: velocity vx (km/s)",
                "Column 6: velocity vy (km/s)",
                "Column 7: velocity vz (km/s)",
                "Column 8: star formation rate (Msun/yr)",
                "Column 9: metallicity (1)", 
                "Column 10: logarithm of the compactness (1)",
                "Column 11: ISM pressure (Pa)",
                "Column 12: PDR covering factor (1)",
                " "
            ]),
            "old": "\n".join([
                "import file for particle source -- old star(TNG50 run)",
                "Column 1: position x (kpc)",
                "Column 2: position y (kpc)",
                "Column 3: position z (kpc)",
                "Column 4: smoothing length (kpc)",
                "Column 5: velocity vx (km/s)",
                "Column 6: velocity vy (km/s)",
                "Column 7: velocity vz (km/s)",
                "Column 8: initial mass (Msun)",
                "Column 9: metallicity (1)",
                "Column 10: age (Gyr)",
                " "
            ]) 
        }
            
    def export_galaxy(self, subhaloID, output_dir):
        """
        从 HDF5 提取并导出 SKIRT 所需的 txt 文件
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            with h5py.File(self.h5_path, 'r') as hdf:
                sid_str = f"Sub{subhaloID}"
                if sid_str not in hdf:
                    logging.error(f"Galaxy {subhaloID} not found in HDF5.")
                    return
                
                gal_grp = hdf[sid_str]
                
                # 1. 导出 Dust (Gas)
                self._export_dust(gal_grp['gas'], output_dir)
                
                # 2. 导出 Stars (分年轻和年老)
                self._export_stars(gal_grp['star'], output_dir)
                
                logging.info(f"TNG {sid_str}\'s data successfully exported to \'{os.path.abspath(output_dir)}\'")
        except Exception as e:
            logging.error(f"TNG {subhaloID} occurs some wrongs: {e}")
            
    def _write_txt(self, filepath, data, header):
        np.savetxt(filepath,
                   data,
                   fmt='%.6e',
                   delimiter='\t',
                   header=header,
                   comments='# '
                  )

    def _export_dust(self, gas_grp, output_dir):
        """导出尘埃组分 (TNG Gas cells)"""
        # 按照 SKIRT 列顺序直接堆叠数据
        # 列：x, y, z, density, metallicity, temperature, vx, vy, vz
        data = np.column_stack([
            gas_grp['x'][:], gas_grp['y'][:], gas_grp['z'][:],
            gas_grp['density'][:], gas_grp['metallicity'][:], gas_grp['temperature'][:],
            gas_grp['vel_x'][:], gas_grp['vel_y'][:], gas_grp['vel_z'][:]
        ])
        
        self._write_txt(os.path.join(output_dir, "dust.txt"), data, self.headers["dust"])

        del data
        gc.collect()

    def _export_stars(self, star_grp, output_dir):
        """将恒星划分为年轻和年老并导出，并确保粒子数为 0 时文件也始终创建"""
        age = star_grp['age'][:]
        # 定义年轻恒星 mask (<= 10 Myr)
        is_young = age <= 0.01
        
        # --- 处理年轻恒星 (MAPPINGS III Source) ---
        if np.any(is_young):
            # 计算 SFR: mass / 1e7 yr
            sfr = star_grp['init_mass'][is_young] / 1e7
            # 模拟 SKIRT 所需的额外参数
            logC = np.random.normal(loc=5, scale=0.4, size=np.sum(is_young))
            p_ism = 1.38e-12 * np.ones(np.sum(is_young))
            f_pdr = np.exp(-age[is_young] / 0.003)
            
            young_data = np.column_stack([
                star_grp['x'][is_young], star_grp['y'][is_young], star_grp['z'][is_young],
                star_grp['hsml'][is_young], 
                star_grp['vel_x'][is_young], star_grp['vel_y'][is_young], star_grp['vel_z'][is_young],
                sfr, star_grp['metallicity'][is_young], logC, p_ism, f_pdr
            ])
            
        else:
            # 如果没有年轻恒星，创建一个空的 (0, 12) 形状数组
            # 12 是年轻恒星 header 定义的列数
            young_data = np.empty((0, 12))
            # logging.info(f"Note: No young stars found for this subhalo. Creating empty youngstar.txt")
            logging.warning(f"Note: No young stars found for this subhalo. Creating empty youngstar.txt")
            
        self._write_txt(os.path.join(output_dir, "youngstar.txt"), young_data, self.headers["young"])
        del young_data

        # --- 处理年老恒星 (Bruzeal-Charlot Source) ---
        is_old = ~is_young
        if np.any(is_old):
            old_data = np.column_stack([
                star_grp['x'][is_old], star_grp['y'][is_old], star_grp['z'][is_old],
                star_grp['hsml'][is_old],
                star_grp['vel_x'][is_old], star_grp['vel_y'][is_old], star_grp['vel_z'][is_old],
                star_grp['init_mass'][is_old], star_grp['metallicity'][is_old], age[is_old]
            ])
        
        else:
            # 10 是年老恒星 header 定义的列数
            old_data = np.empty((0, 10))
            
        self._write_txt(os.path.join(output_dir, "evolvedstar.txt"), old_data, self.headers["old"])
        del old_data
        
        del age, is_young, is_old
        gc.collect()

# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    h5_file = "TNG50_1_326914.hdf5"
    exporter = SubhaloDataExporter(h5_file)
    
    target_id = 326914
    exporter.export_galaxy(target_id, f"./input_files/{target_id}")
    
    