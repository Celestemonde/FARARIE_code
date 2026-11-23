# HPC Module

This module contains Python scripts for running SKIRT radiative transfer simulations on an HPC cluster.

## Directory Structure

| File / Folder | Description |
|---|---|
| `script/` | Core Python scripts for the simulation pipeline (see below) |
| `mergerhdf.py` | Merges multiple HDF5 output files into a single file; use this when processing multiple galaxies |
| `GNUbash.sh` | SLURM batch script for running SKIRT on an HPC cluster; submit with `sbatch GNUbash.sh` |

## Scripts (`script/`)

| Script | Description |
|---|---|
| `data_builder.py` | Converts preprocessed HDF5 data into SKIRT-compatible `.txt` input files |
| `skirt_runner.py` | Executes SKIRT simulations *(currently supports single-galaxy runs only; advanced SKIRT features not yet implemented)* |
| `post_processor.py` | Reads SKIRT output `.fits` files and writes results into HDF5 format *(currently supports `total.fits` and `stats0–4.fits`; SED output and other SKIRT probes are not included)* |
| `main.py` | Integrates all the above scripts and runs the full pipeline end-to-end |

## Usage

**On an HPC cluster (SLURM):**
```bash
sbatch GNUbash.sh
```

**On a regular server:**
```bash
python script/main.py
```

## Notes

> **Before running**, make sure all required data files are prepared and placed in the correct directories.
> Currently, all file paths are hardcoded as absolute paths — update them as needed for your environment.

- After a successful run, `main.py` will **delete the simulation folder** and store results in the corresponding HDF5 file.
  If you wish to retain the simulation folder, comment out the relevant lines in `main.py`.
- For the expected file structure, see `02_skirt/HPC/files organization.png`.

## Acknowledgement

The parallelisation in `GNUbash.sh` relies on [GNU Parallel](https://www.gnu.org/software/parallel/). As required by its author, any work that uses GNU Parallel should include the following citation:

> Tange, O. (2011). GNU Parallel - The Command-Line Power Tool. *;login: The USENIX Magazine*, 36(1), 42–47. https://doi.org/10.5281/zenodo.16303

## References

- SKIRT import snapshot: https://skirt.ugent.be/root/_user_import_snap.html
- Running SKIRT with Python: https://skirt.ugent.be/root/_tutorial_python.html
- Modifying `.ski` files: https://skirt.ugent.be/root/_user_param_file.html and refer to the SKIRT XML syntax documentation.


# Mock Image Module

This module contains 3 Python scripts and 1 `.ski` file.

## Scripts

| Script | Description |
|---|---|
| `getdata.py` | Converts preprocessed TNG data into SKIRT-compatible `.txt` input format |
| `outputfile.py` | Reads SKIRT output `.fits` files (simulated images and statistics W0–W4) and writes them into HDF5 |
| `multiprorun.py` | Executes the full pipeline end-to-end |

## Notes

> This pipeline is intended for **small-scale runs on a regular server**. File paths are hardcoded as absolute paths — update them as needed for your environment.

This pipeline's code logic was developed in 2025. A newer version is available at `tng-skirt-pipeline/02_skirt/HPC`. Both versions are functional and can be run as-is.

---

# SED Module

The code structure here is similar to the Mock Image module, but is used to output **SED files** instead of images. The `instrument` configured in the `.ski` file also differs from the one used in the Mock Image module.

# Others

`plot_bands.ipynb` is a simple example for visualizing SKIRT's built-in broadbands.

## References

- Broadband documentation: https://skirt.ugent.be/root/_user_broadbands.html
- https://skirt.ugent.be/skirt9/class_band.html
- PTS source code （ XXXXXX/PTS/pts/band/broadband.py ）

Linux relates:
- https://itsfoss.com/basic-terminal-tips-ubuntu/

HPC relates:
- https://crc-pages.pitt.edu/user-manual/slurm/job-arrays/
- https://slurm.schedmd.com/faq.html#hold
- https://ai4ec.ac.cn/ikkem-hpc/doc/slurm/sbatch/
- https://daic.tudelft.nl/docs/manual/job-submission/slurm-advanced/
- https://docs.hpc.sjtu.edu.cn/job/jobsample1.html
- https://www.yeesuan.com/doc/zh/%E7%81%B5%E7%8A%80%E6%98%93%E7%AE%97%E4%BA%91%E5%B9%B3%E5%8F%B0/%E9%AB%98%E6%80%A7%E8%83%BD%E8%AE%A1%E7%AE%97%EF%BC%88HPC%EF%BC%89%E5%BF%AB%E9%80%9F%E5%85%A5%E9%97%A8.html
