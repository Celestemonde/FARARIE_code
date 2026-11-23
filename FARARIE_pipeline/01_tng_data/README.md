# TNG Data Preprocessing

## Notebook

`preprocess.ipynb` preprocesses **star particles** and **gas cells** data for a single subhalo from a TNG snapshot. It converts the relevant quantities into the units required for SKIRT input and exports the result as an HDF5 file.

> **Note:** This notebook is designed to run on the **IllustrisTNG JupyterLab server**. If you instead download subhalo data via the API, you will need to adapt the code accordingly (e.g. data loading and path handling).

## References

**General TNG data processing:**
- Example scripts: https://www.tng-project.org/data/docs/scripts/
- API documentation: https://www.tng-project.org/data/docs/api/

**Data specifications:**
- https://www.tng-project.org/data/docs/specifications/

**Questions about TNG usage:**
- Forum: https://www.tng-project.org/data/forum/
- FAQ: https://www.tng-project.org/data/docs/faq/