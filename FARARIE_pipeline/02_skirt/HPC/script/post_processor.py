import os
import h5py
import logging
import gc
from concurrent.futures import ProcessPoolExecutor
from astropy.io import fits
import pts.simulation as sm

def _read_fits_task(outpath, prefix, view_name, dataset_map):
    """
    读取单个 FITS 文件。
    只接收字符串参数，返回处理后的 NumPy 数据。
    """
    view_data = {}
    try:
        for label, suffix in dataset_map.items():
            # 拼接文件名：例如 JWSTmock_Face-on_total.fits
            filename = f"{prefix}_{view_name}_{suffix}.fits"
            filepath = os.path.join(outpath, filename)
            
            # if not os.path.exists(filepath):
            #     continue
                
            with fits.open(filepath) as hdul:
                data = hdul[0].data
                h = hdul[0].header
                
                # 提取波长
                z_info = None
                if int(h['NAXIS']) > 2 and "Z-axis coordinate values" in hdul:
                    hdu_z = hdul["Z-axis coordinate values"]
                    z_val = hdu_z.data["GRID_POINTS"].astype(float)
                    z_unit = str(hdu_z.header.get("TUNIT1", "micron"))
                    z_info = (z_val, z_unit)
                    header_zaxis = hdul[1].header.tostring()    
                else:
                    header_zaxis = None
                
                header_data = h.tostring()
                
                view_data[label] = (data, z_info, header_data, header_zaxis)
        return view_name, view_data
    except Exception as e:
        return view_name, str(e)

class PostProcessor:
    def __init__(self, subhalo_id, outpath, result_path, outmode='single', dataset_map=None):
        
        if outmode not in ("single", "batch"):
            raise ValueError(f"mode must be 'single' or 'batch', got '{mode}'")
        else:
            if outmode == "batch":
                self.output_hdf5 = os.path.join(result_path, "result.hdf5")
            else:
                self.output_hdf5 = os.path.join(result_path, f"{subhalo_id}.hdf5")
                
        self.subhalo_id = subhalo_id
        self.outpath = os.path.abspath(outpath)
        # 允许外部自定义映射，否则使用默认值
        self.dataset_map = dataset_map or {
            "image": "total",
            "W0": "stats0",
            "W1": "stats1", 
            "W2": "stats2",
            "W3": "stats3",
            "W4": "stats4"
        }

    def process_all_views(self, prefix, view_names, max_workers=None):
        """
        核心函数：并行读取各视角，完成后串行写入 HDF5
        prefix：模拟名称
        view_names：
        """
        logging.info(f"Loading simulation results for Subhalo {self.subhalo_id}: {len(view_names)} views.")

        # 使用 ProcessPoolExecutor 进行并行读取
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务，只传递 str 类型的路径和前缀
            future_to_view = {
                executor.submit(_read_fits_task, self.outpath, prefix, v, self.dataset_map): v 
                for v in view_names
            }

            # 串行写入 HDF5
            with h5py.File(self.output_hdf5, 'a') as hdf:
                sub_grp = hdf.require_group(f'Sub_{self.subhalo_id}')
                
                for future in future_to_view:
                    view_name, result = future.result()
                    
                    if isinstance(result, str):
                        logging.error(f"Error processing {view_name}: {result}")
                        continue
                    
                    # 写入对应的组
                    logging.info(f"Writing view: {view_name}")
                    self._save_view_data(sub_grp.require_group(view_name), result)
                    
                    # 及时回收内存
                    result.clear()
                    gc.collect()
                    
        logging.info(f"Results have been saved to \'{os.path.abspath(self.output_hdf5)}\'.")

    def _save_view_data(self, view_group, data_dict):
        """内部写入逻辑"""
        for label, (dcube, z_info, header_data, header_zaxis) in data_dict.items():
            # if label in view_group: del view_group[label]
            
            ds = view_group.create_dataset(
                label, data=dcube, 
                compression='gzip', compression_opts=4
            )
            
            ds.attrs['header'] = header_data
            ds.attrs['header_zaxis'] = header_zaxis
            
            if z_info:
                z_val, z_unit = z_info
                ds.attrs['pivot_wavelength'] = z_val
                ds.attrs['zaxis_unit'] = z_unit
            else:
                ds.attrs['type'] = "2D_Image"  
                
                
#     def _save_view_data_v2(self, view_group, view_data):
#         """ 
#         后备 V2 方案：按波长拆分，每个波段是独立的 Dataset 
#         """
#         for label, (dcube, z_info, header_data, header_zaxis) in view_data.items():
#             # 为每个数据类型创建一个 Group，例如 /image/, /W0/
#             label_group = view_group.require_group(label)
            
#             if z_info:
#                 z_vals, z_unit = z_info
#                 # 遍历波长轴
#                 for i, wl_val in enumerate(z_vals):
#                     # 构造数据集名字，例如 "PiWav:1.15430 micron"
#                     ds_name = f"PiWav:{wl_val:.5f} {z_unit}"
                    
#                     if ds_name in label_group: del label_group[ds_name]
                    
#                     ds = label_group.create_dataset(
#                         ds_name, 
#                         data=dcube[i], # 写入第 i 层图像
#                         compression='gzip', 
#                         compression_opts=4
#                     )
#                     ds.attrs['header'] = header_data
#                     ds.attrs['header_zaxis'] = header_zaxis
#                     ds.attrs['pivot_wavelength'] = wl_val
#                     ds.attrs['unit'] = z_unit
#             else:
#                 # 处理单帧 (2D)
#                 ds_name = "Single_Frame"
#                 if ds_name in label_group: del label_group[ds_name]
#                 label_group.create_dataset(ds_name, data=dcube, compression='gzip')