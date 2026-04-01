import subprocess
import time

from pathlib import Path
from datetime import datetime

size_min, size_max = 3, 36
width = 6

dumps_folder = f"dumps/{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
logs_folder = f"logs/{datetime.now().strftime('%Y-%m-%d_%H-%M')}"

Path(dumps_folder).mkdir(parents=True, exist_ok=True)
Path(logs_folder).mkdir(parents=True, exist_ok=True)

start_time = time.perf_counter()

for size in range(size_min, size_max + 1, 1):
    command = f'''
        mpirun -np 2 lmp
        -var xlen {size}
        -var ylen {width}
        -var zlen {size}
        -var dump_name {f'{dumps_folder}/{size}x{width}x{size}.atom'}
        -var log_name {f'{logs_folder}/{size}x{width}x{size}.log'}
        -in plc-md.lmp
    '''.split()
    
    subprocess.run(command, check=True)

end_time = time.perf_counter()

print("--- --- ---")
print(f"TOTAL TIME ELAPSED: {(end_time - start_time):.4f} sec")
print("--- --- ---")