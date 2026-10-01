import time
import csv
import os
import numpy as np

from argparse import ArgumentParser
from pathlib import Path

from ovito.io import import_file
from ovito.modifiers import DislocationAnalysisModifier, \
                            ExpressionSelectionModifier


if os.getcwd().endswith('src'): os.chdir('..')

INPUT_DIR = Path('dumps/equilibrations')
OUTPUT_DIR = Path('results/lc')

RADIUS_DIV = 40 # how many different radiuses is compared
RADIUS_MIN = 20 # minimal radius, [Ang]


if __name__ == '__main__':

    """
    STEP 0: parse script arguments

    getting input (dump) and output (csv) file names
    """

    parser = ArgumentParser(description='OVITO local solute saturation concentration in Cottrell atmospheres analysis.')

    parser.add_argument('-i', '--input', type=Path, help='relative path to the input LAMMPS dump file')
    parser.add_argument('-o', '--output', type=Path, help=f'output csv file name (filename only, without extension). Will be saved at ./{OUTPUT_DIR}')

    args = parser.parse_args()

    if not args.input:
        # get latest file in the directory
        args.input = max(filter(lambda x: x.is_file(), INPUT_DIR.iterdir()), key=lambda x: x.stat().st_mtime)
        print(f'Input file name was not provided, using latest dump file: {args.input}')

    if not args.output:
        # create directory for calculation results if it doesn't exist and save output there
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        args.output = OUTPUT_DIR / Path(args.input.name).with_suffix('.csv')

    # rename with a number ("file_(n).csv") if file exists
    counter = 1
    while args.output.exists():
        args.output = args.output.with_name(args.output.stem.replace(f'_({counter - 1})', '') + f'_({counter}){args.output.suffix}')
        counter += 1

    """
    STEP 1: modifiers configuration

    finding the dislocation and preparing the selection around it
    """

    start_time = time.time()

    print(f'Importing file: {args.input}')

    # import file
    # LAMMPS dump columns: id type x y z
    pipeline = import_file(args.input, columns=[
        'Particle Identifier', 'Particle Type',
        'Position.X', 'Position.Y', 'Position.Z'
    ])

    print(f'File imported in {(time.time() - start_time):.2f} sec.')

    # 1. finding actual dislocation lines and marking atoms that belong to them
    dxa_mod = DislocationAnalysisModifier(
        input_crystal_structure=DislocationAnalysisModifier.Lattice.FCC,
        mark_dislocation_core_atoms=True
    )
    pipeline.modifiers.append(dxa_mod)

    # 2. append a placeholder expression selection modifier
    #    (dynamically changed in the main loop)
    sel_mod = ExpressionSelectionModifier(
        expression='1'
    )
    pipeline.modifiers.append(sel_mod)

    """
    STEP 2: actual computing

    c = c(r), where
    c - local concentration of Mg: c=\frac{N_{Mg}(r)}{N_{Mg}(r)+N_{Al}(r)}
    r - radius of the cylinder with the center at dislocation's core
    """

    # getting data from the last simulated frame
    last_frame = pipeline.num_frames - 1
    data = pipeline.compute(last_frame)

    # NOTE: we assume there actually is a dislocation in the file provided :)

    # coordinates of the dislocation's core
    positions = data.particles.positions[data.particles['Dislocation'] != -1]

    core_x = np.mean(positions[:, 0])
    core_y = np.mean(positions[:, 1])

    w = data.cell[0, 0] # length in X direction
    h = data.cell[1, 1] # length in Y direction

    # finding max distance from dislocation's core to cell's edges
    # => all atoms in the cell will be inside the cylinder with radius r_max
    r_max = np.max([
        ( core_x**2       + core_y**2       ) ** 0.5,
        ( core_x**2       + (h - core_y)**2 ) ** 0.5,
        ( (w - core_x)**2 + core_y**2       ) ** 0.5,
        ( (w - core_x)**2 + (h - core_y)**2 ) ** 0.5
    ])
    r_mult = r_max - RADIUS_MIN

    # removing dxa from the pipeline as we don't need it no more
    pipeline.modifiers.remove(dxa_mod)

    expr_part = f'(Position.X - {core_x})^2 + (Position.Y - {core_y})^2'

    print()
    print(f'Dislocation\'s core coordinates: ({core_x:.2f}, {core_y:.2f}).')
    print(f'Computing c_Mg for {RADIUS_DIV} radiuses ranging linearly from {RADIUS_MIN:.2f} to {r_max:.2f}.')
    print(f'Using expression: {expr_part} < r^2. (variable "r")')
    print()

    with open(args.output, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['r', 'c'])

        for i in range(0, RADIUS_DIV + 1):
            r = r_mult * (i / RADIUS_DIV) + RADIUS_MIN

            # TODO: perhaps there are better ways to do this stuff

            expr = f'{expr_part} < {r}^2'

            sel_mod.expression = f'{expr} && ParticleType == 2'
            data = pipeline.compute(last_frame)
            N_mg = np.sum(data.particles['Selection'])

            sel_mod.expression = expr
            data = pipeline.compute(last_frame)
            N = np.sum(data.particles['Selection'])

            c = N_mg / N

            print(f'c({r:.4f})\t= {c:.4f}')
            writer.writerow([r, c])

    print(f'\nOutput file: {args.output}')
