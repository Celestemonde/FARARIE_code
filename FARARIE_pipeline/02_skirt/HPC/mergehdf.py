import h5py
import glob
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

input_files = sorted(glob.glob("./result/*.hdf5"))

# revised here's filename
with h5py.File("STRATA_z3p0_1e7.hdf5", "w") as fout:
    for fname in input_files:
        
        with h5py.File(fname, "r") as fin:
            
            # 找到顶层 group（假设只有一个）
            keys = list(fin.keys())
            if len(keys) != 1:
                raise ValueError(f"{fname} has multiple root groups: {keys}")
            
            root = keys[0]   # e.g. Sub_503987
            
            # print(f"Copying {root} from {fname}")
            
            # 直接复制整个 group
            fin.copy(root, fout)
            
            logging.info(f"File {fname} has been processed.")
            
logging.info('Finished.')
