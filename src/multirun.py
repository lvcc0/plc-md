import subprocess
import time
import os

from pathlib import Path
from datetime import datetime


if os.getcwd().endswith('src'): os.chdir('..')

SIZE_X = 99
SIZE_Y = 40
SIZE_Z = 8

VAC_FRACS = (0.0, 0.001)
DESIRED_TEMPS = (300, 350, 400)

if __name__ == '__main__':

    times: dict[str, float] = {}

    # check for initial lattice atom file
    if not any(Path('.').glob('*.pad')):
        # compile lattice generating script if it is not yet compiled
        if not Path('latgen').exists():
            print('"latgen" doesn\'t exist, compiling now...')
            subprocess.run('gfortran -O2 src/latgen.f90 -o latgen'.split(), check=True)

        # create initial lattice atom file using fortran script
        subprocess.run(
            './latgen',
            input='\n'.join(map(str, [SIZE_X, SIZE_Y, SIZE_Z, 2])) + '\n',
            text=True,
            check=True
        )

    start_time = time.time()

    for vac_frac in VAC_FRACS:
        for desired_temp in DESIRED_TEMPS:
            local_start_time = time.time()

            iteration_id = f'{(vac_frac * 100.0):g}vac_{desired_temp}temp'
            file_name = f'{datetime.now().strftime("%d-%m_%H-%M")}_{iteration_id}'

            subprocess.run(
                f"""
                    ./run.sh src/in.equilibration
                    -var vac_frac {vac_frac}
                    -var desired_temp {desired_temp}
                    -var file_name {file_name}
                """.split(),
                check=True
            )

            # save time elapsed for this iteration
            times[iteration_id] = time.time() - local_start_time

    print(f'\nTotal time elapsed: {(time.time() - start_time):.2f} sec')

    print('Time elapsed for each iteration:')
    for key, val in times.items():
        print(f'{key}:\t{val:.2f}')
