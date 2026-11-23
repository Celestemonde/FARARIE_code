"""
从包含TNG snapshot数据的HDF5文件中，再加工，输出dust，star文件到用于skirt模拟的输入文件夹中。
需要创建好输入文件夹，放入filter文件
"""
import h5py
import numpy as np
import pandas as pd
import os
import logging

def ProcessHDF(filepath, galaxy_id):
    with h5py.File(filepath, 'r') as hdf:
        
        gas = hdf[f'{galaxy_id}']['gas']
        dust_dict = {'x': gas['x'][:],    # kpc
                     'y': gas['y'][:],    # kpc
                     'z': gas['z'][:],    # kpc
                     'density': gas['density'][:],    # M_sun/pc3
                     'metallicity': gas['metallicity'][:],    # 1
                     'temperature': gas['temperature'][:],    # K
                     'vel_x': gas['vel_x'][:],    # km/s
                     'vel_y': gas['vel_y'][:],    # km/s
                     'vel_z': gas['vel_z'][:],    # km/s
                     }
        
        star = hdf[f'{galaxy_id}']['star']
        star_dict = {'x': star['x'][:],    # kpc
                     'y': star['y'][:],    # kpc
                     'z': star['z'][:],    # kpc
                     'hsml': star['hsml'][:],    # kpc
                     'vel_x': star['vel_x'][:],    # km/s
                     'vel_y': star['vel_y'][:],    # km/s
                     'vel_z': star['vel_z'][:],    # km/s
                     'init_mass': star['init_mass'][:],    # M_sun
                     'metallicity': star['metallicity'][:],    # 1
                     'age': star['age'][:],    # Gyr
                     'form_time': star['form_time'][:],    # 1 (a)
                     'normalized_hsml': star['normalized_hsml'][:],    # 1
                     }
        
        return dust_dict, star_dict
        

class ProcessStarData():
    
    def star_divided(self, star_dict):
        # 以 10Myr(0.01 Gyr) 为标准将star分为年轻恒星和年老恒星

        young_index = np.where(star_dict['age'] <= 0.01)[0]
        young_star = {'x': star_dict['x'][young_index],    # kpc
                      'y': star_dict['y'][young_index],    # kpc
                      'z': star_dict['z'][young_index],    # kpc
                      'hsml': star_dict['hsml'][young_index],    # kpc (TNG提供了两种smoothing length, 这里选择用stellar定义的)
                      'vel_x': star_dict['vel_x'][young_index],    # km/s
                      'vel_y': star_dict['vel_y'][young_index],    # km/s
                      'vel_z': star_dict['vel_z'][young_index],    # km/s
                      'SFR': star_dict['init_mass'][young_index] / 1e7,    # M_sun/yr（年轻恒星的界限是10Myr，即1e7yr，假定恒星形成速率是恒定的）
                      'metallicity': star_dict['metallicity'][young_index],    # 1
                      'logC': np.random.normal(loc=5, scale=0.4, size=len(young_index)),    # 1
                      'ISM_pressure': 1.38*1e-12*np.ones(len(young_index)),    # Pa
                      'PDR_factor': np.exp(-star_dict['age'][young_index]/0.003),    # 1
                      'normalized_hsml': star_dict['normalized_hsml'][young_index]      # 1 (仅用于分组，后面要删除)
                      }
        
        aged_index = np.where(star_dict['age'] > 0.01)[0]
        aged_star = {k: v[aged_index] for k, v in star_dict.items()}
        aged_star.pop('form_time')

        return young_star, aged_star

    
    # n组分分法
    def split_star(self, star_dict, num):
        # 获取 normalized_hsml 数组
        normalized_hsml = star_dict['normalized_hsml']

        # 对数据按 normalized_hsml 排序，同时保持所有键值对的一一对应关系
        sorted_indices = np.argsort(normalized_hsml)
        sorted_star = {key: np.array(value)[sorted_indices] for key, value in star_dict.items()}

        # 获取排序后的 normalized_hsml 数组
        sorted_normalized_hsml = sorted_star['normalized_hsml']
        sorted_star.pop('normalized_hsml')
        
        # 获取数据的总数量
        n_data = len(sorted_normalized_hsml)

        # 如果数据数量小于等于 10，每个数据自成一组
        # if n_data != 0 and n_data <= num:  
        #     n_groups = n_data  
        # elif n_data == 0:  # 显式处理 n_data=0  
        #     n_groups = 1  
        # else:  
        #     n_groups = num 
        n_groups = n_data if (n_data != 0 and n_data <= num) else num
        # n_groups = n_data if n_data <= num else num

        # 计算每组的大小，最后一组可以包含剩余的数据
        group_size = n_data // n_groups
        remainder = n_data % n_groups

        # 预分配每组的空间
        grouped_data = {i: {key: [] for key in sorted_star} for i in range(n_groups)}

        # 按照顺序分配数据到各个组中
        index = 0
        for i in range(n_groups):
            # 每个组至少包含 group_size 个数据
            group_end = index + group_size + (1 if i >= n_groups - remainder else 0)  # 剩余数据分配给最后几个组
            for key in sorted_star:
                grouped_data[i][key] = sorted_star[key][index:group_end]
            index = group_end

        return grouped_data
    
    
    def work(self, star_dict, n1, n2):
        """
        将 star_dict分为年轻恒星和年老恒星，这两类恒星分成 n1, n2 份
        """
        young_star, aged_star = self.star_divided(star_dict)
        
        # 两类恒星各自分组
        young_group = self.split_star(young_star, n1)
        aged_group = self.split_star(aged_star, n2)

        return young_group, aged_group
    
    
    def cal_statis_and_weights(self, grouped_data):
        """
        计算每个组的 normalized_hsml 的中位数，并计算每个组的权重。

        参数:
            grouped_data (dict): 每组数据的字典，包含多个字段。

        返回:
            weights (list): 每组的权重。
        """
        medians = []

        # 计算中位数
        for group_index, group in grouped_data.items():

            hsml = group['hsml']
            hsml_data = np.power(hsml, 2)

            medians.append(np.median(hsml_data))

        # 计算权重：基于中位数，归一化使得权重之和为1
        total_median = np.sum(medians)
        weights = [median / total_median for median in medians]

        return weights
    

def makeFHDUs(filepath, id, n1=1, n2=10):
    """
    filepath: 储存TNG snapshot数据的HDF5文件所在的路径
    id: 需要被输出模拟的星系ID
    n1: 年轻恒星被分成的份数
    n2: 年老恒星被分成的份数
    """
    # 写入txt文件所需的 Header
    header_dust = [
        "# import file for Voronoi mesh media -- dust(TNG50 run)",
        "# Column 1: position x (kpc)",
        "# Column 2: position y (kpc)",
        "# Column 3: position z (kpc)",
        "# Column 4: dust mass density (Msun/pc3)",
        "# Column 5: metallicity (1)",
        "# Column 6: temperature (K)",
        "# Column 7: velocity vx (km/s)",
        "# Column 8: velocity vy (km/s)",
        "# Column 9: velocity vz (km/s)",
        "# "
        ]

    header_youngstar = [
        "# import file for particle source -- young star(TNG50 run)",
        "# Column 1: position x (kpc)",
        "# Column 2: position y (kpc)",
        "# Column 3: position z (kpc)",
        "# Column 4: smoothing length (kpc)",
        "# Column 5: velocity vx (km/s)",
        "# Column 6: velocity vy (km/s)",
        "# Column 7: velocity vz (km/s)",
        "# Column 8: star formation rate (Msun/yr)",
        "# Column 9: metallicity (1)", 
        "# Column 10: logarithm of the compactness (1)",
        "# Column 11: ISM pressure (Pa)",
        "# Column 12: PDR covering factor (1)",
        "# "
        ]

    header_agedstar = [
        "# import file for particle source -- old star(TNG50 run)",
        "# Column 1: position x (kpc)",
        "# Column 2: position y (kpc)",
        "# Column 3: position z (kpc)",
        "# Column 4: smoothing length (kpc)",
        "# Column 5: velocity vx (km/s)",
        "# Column 6: velocity vy (km/s)",
        "# Column 7: velocity vz (km/s)",
        "# Column 8: initial mass (Msun)",
        "# Column 9: metallicity (1)",
        "# Column 10: age (Gyr)",
        "# "
        ]

    headers = [header_dust] + [header_youngstar for _ in range(n1)] + [header_agedstar for _ in range(n2)]
    filenames = ["dust.txt"] + [f"youngstar{i+1}.txt" for i in range(n1)] + [f"agedstar{i+1}.txt" for i in range(n2)]
    
    dust_dict, star_dict = ProcessHDF(filepath, galaxy_id=id)
    
    young_group, aged_group = ProcessStarData().work(star_dict, n1, n2)      
    
    dataframes = [pd.DataFrame(dust_dict)] + [pd.DataFrame(group) for group in young_group.values()] + [pd.DataFrame(group) for group in aged_group.values()]
    
    FHDUs = zip(filenames, headers, dataframes)
    
    # 计算年老恒星的权重
    # young_weights = cal_statis_and_weights(young_group)
    aged_weights = ProcessStarData().cal_statis_and_weights(aged_group)
    
    return FHDUs, aged_weights

    
def export_data(id, FHDUs, galaxyPath):
    """
    定义导出数据为txt文件的函数
    id: 被获取数据的星系编号
    FHDUS: 处理后的数据块
    galaxyPath: 存放处理后数据的文件夹路径，即SKIRT模拟的输入文件夹位置
    """
    # output_dir = "/data/suminxian/SHNU/galaxy"
    try:  
        # 确保输出目录存在
        os.makedirs(galaxyPath, exist_ok=True)

        # 写入数据文件
        for filename, header, dataframe in FHDUs:
            filepath = os.path.join(galaxyPath, filename)

            # w 模式，不同id的星系模拟时会覆盖旧数据，先写入header信息
            with open(filepath, "w") as f:
                f.writelines(f"{line}\n" for line in header)

            # 数据部分用 a 模式追加
            dataframe.to_csv(filepath, sep="\t", mode="a", index=False, header=False)
            
        logging.info(f"TNG {id} 's data successfully exported to directory: {galaxyPath}")
    
    except Exception as e:
        logging.info(f"TNG {id} occurs some wrongs:{e}")

    
# if __name__ == '__main__':
    
#     FHDUs, _ = makeFHDUs(filepath="TNG50_snapshot.hdf5", id=514272)
#     export_data(514272, FHDUs)