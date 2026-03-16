import subprocess
import time

from pathlib import Path
from datetime import datetime

size_min, size_max = 6, 48

folder = f"dumps/{datetime.now().strftime("%Y-%m-%d_%H-%M")}"
Path(folder).mkdir(parents=True, exist_ok=True)

start_time = time.perf_counter()

for size in range(size_min, size_max + 1, 3):
    command = f'''
        mpirun -np 2 lmp
        -var xlen {size}
        -var zlen {size}
        -var dump_name {f'{folder}/{size}x{size}.atom'}
        -in plc-md.lmp
    '''.split()
    
    subprocess.run(command, check=True)

end_time = time.perf_counter()

print("--- --- ---")
print(f"TOTAL TIME ELAPSED: {(end_time - start_time):.4f} sec")
print("--- --- ---")