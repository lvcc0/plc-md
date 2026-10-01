# NOTE: soon to be refactored

import subprocess
import time
import os

from pathlib import Path
from datetime import datetime


if os.getcwd().endswith('src'): os.chdir('..')

SIZE_Z: int = 4
SIZES: list[tuple[int, int]] = [(int(2.5 * y) - (not int(2.5 * y) % 2), y) for y in range(2, 33, 2)]

# X - odd, Y - even
# Y \approx (0.4 X) => X /approx (2.5 Y)

if __name__ == '__main__':

    folder: str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    times: dict[str, float] = {}

    # create all necessary directories
    for root in ['logs/equilibrations', 'dumps/equilibrations', 'restarts/equilibrations']:
        Path(f'{root}/{folder}').mkdir(parents=True, exist_ok=True)

    if not Path('lattice_generator').exists():
        print('"lattice_generator" doesn\'t exists, compiling now...')
        subprocess.run('gfortran -O2 src/lattice_generator.f90 -o lattice_generator'.split(), check=True)

    start_time = time.time()

    for size_x, size_y in SIZES:
        local_start_time = time.time()

        # create initial lattice atom file using fortran script
        subprocess.run(
            './lattice_generator',
            input='\n'.join(map(str, [size_x, size_y, SIZE_Z, 2])) + '\n',
            text=True,
            check=True
        )

        atom_file = f'atoms.{size_x}x{size_y}x{SIZE_Z}.pad'
        file_name = f'{folder}/{size_x}x{size_y}x{SIZE_Z}'

        # run equilibration using generated lattice atom file
        subprocess.run(
            f"""
                mpirun -np 2 lmp
                -var atom_file {atom_file}
                -var file_name {file_name}
                -in src/in.equilibration
            """.split(),
            check=True
        )

        # delete generated lattice atom file
        Path(atom_file).unlink()

        # save time elapsed for this iteration
        times[f'{size_x}x{size_y}x{SIZE_Z}'] = time.time() - local_start_time

    print(f'\nTotal time elapsed: {(time.time() - start_time):.2f} sec')
    print('Time elapsed for each iteration:')

    for key, val in dict(sorted(times.items(), key=lambda x: int(x[0].split('x')[0]))):
        print(f'{key}: {val:.2f}')
