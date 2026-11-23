# 仓库中包含两部分的代码

## 01_tng_data

这是一个 `ipynb` 文件，需要在 IllustrisTNG 的服务器上使用，如果是本地服务器数据使用的话需要确保文件路径的一致。

但是里面的代码详细描述了从 TNG50 snapshot 数据获取 SKIRT 所需要的 fields，然后再输出为一个 `hdf5` 的流程。

这样做的目的是，TNG50 的整个 snapshot 文件很大，但是本例中的 SKIRT 模拟只用到了 central galaxy 的 
gas particles（PartType 0） 与 star particles(PartType 4) 的数据，为此对于每一个 subhalo 样本，先分别
提取出相应的必要数据，然后后续模拟的时候可以批量进行模拟。

代码中包含了将星系的三个主轴对齐到 xyz 轴的操作，如果不需要对齐将相应部分的代码注释即可。

数据处理参考了： Baes et al. (2024) **The TNG50-SKIRT Atlas: Post-processing methodology and firstdata release** 的方法部分。
文章链接：https://www.aanda.org/articles/aa/full_html/2024/03/aa48418-23/aa48418-23.html

## 02_skirt
### mock images file

这里 FARARIE 项目主要用到的代码是 mock images 文件夹下的 `ski` 文件以及 python 文件。

* `getdata` 是将预处理过的 TNG 数据（step 1 输出的 `hdf5` 文件）中的数据，按单个 subhalo 提取出来并处理成 SKIRT 所需要的 `.txt`
文件格式。
* `outputfile` 是将模拟结束的 SKIRT 输出从 `.fits` 转存到 `hdf5` 格式，便于处理大量 subhalo 数据时单一文件存储。
* `multiprun` 是真正运行 `skirt` 模拟的文件，负责串联另外两个 `.py` 文件。使用时只需输入 `python multiprun.py` 即可
运行(理论上，但是在其他环境下可能由于路径，文件名设置之类的问题会报错。需要仔细检查。)
* `FARARIE` 文件则是 SKIRT 的配置文件。

### HPC file
* `script` 这个文件夹下的脚本是为了适配使用 `slurm` 的超算编写的，其中 `script` 的 python 文件当时使用 AI 辅助进行了重构，理论上是前面的 python
文件的升级版。

* `skifile` 同样的是 SKIRT9 的配置文件，部分配置如 `instrument` 的设置略有不同。
*  `tasks` 只是一些 subhalo id 构成的 txt 文件，用于 python 模拟的文件中读取然后运行模拟的。
*  `GNUbash.sh` 是超算上提交作业的文件，不适用超算可以忽略。


## 其他
实际模拟时的运行时间取决于模拟使用的光子数以及这个星系本身的尘埃数量（影响光深及辐射转移时的运算）。一般来说使用 $10^7$ 光子的运行速度只需要几分钟，
但是得到的图像在目前设定的 `instrument` 分辨率下的信噪比很低。至少需要 $10^9$ 光子才可得到信噪比较高的图像，但是那在使用 24 core 运行的情况
下通常需要 12 个小时的运行时长。
