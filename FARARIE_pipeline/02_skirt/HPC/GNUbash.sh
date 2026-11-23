#!/bin/bash
#SBATCH -J MCRT
#SBATCH -p cn
#SBATCH --array=0-9
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --cpus-per-task=192
#SBATCH --mem=256G
#SBATCH --output=logs/%A_%a.out
#SBATCH --error=logs/%A_%a.err
#SBATCH --time=48:00:00
#SBATCH --exclusive

export OMP_NUM_THREADS=24
export OMP_PROC_BIND=true
export OMP_PLACES=cores

NODE_ID=$(printf "%01d" ${SLURM_ARRAY_TASK_ID})
export redshift="z3p0"  # 不同红移改这里！
GALAXY_LIST="./tasks/${redshift}/node_${NODE_ID}.txt"  # 需要更改实际 galaxy list 的路径

echo "=== Node ${NODE_ID} | Job ${SLURM_JOB_ID} | Host $(hostname) ==="

run_galaxy() {
    GALAXY_ID=$1
    
    echo "[$(date +%H:%M:%S)] START ${GALAXY_ID}"

    python ./script/main.py \
        -g ${GALAXY_ID} \
        -f "/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/raw_data/TNG50_${redshift}.hdf5" \
        -k "/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/skifile/${redshift}.ski" \
        -m "single" \
        -p "April" \
        -o "/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/result" \
        -n 1e7 \
        -S 0 \
        -t 24 \
        -w 7
        
    EXIT_CODE=$?
    echo "[$(date +%H:%M:%S)] DONE ${GALAXY_ID} (exit: ${EXIT_CODE})"
}

export -f run_galaxy

parallel -j 8 --tag \
    --joblog "/n96pfs/home/ysn96pc0086/yeesuan/TNG_MCRT_Project/GNUlogs/parallel_${NODE_ID}.log" \
    run_galaxy {} \
    :::: "${GALAXY_LIST}"
    
echo "=== Node ${NODE_ID} ALL DONE ==="


 
