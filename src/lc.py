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

RADIUS_MIN = 20 # minimal radius, [Ang]
RADIUS_STEP = 5 # adding this to radius every iteration, [Ang]


def process_dump(dumpname) -> dict[float, float]:
    start_time = time.time()

    """
    STEP 1: modifiers configuration

    finding the dislocation and preparing the selection around it
    """

    print(f'Importing file: {dumpname}')

    # import file
    # LAMMPS dump columns: id type x y z
    pipeline = import_file(dumpname, columns=[
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

    # removing dxa from the pipeline as we don't need it no more
    pipeline.modifiers.remove(dxa_mod)

    # NOTE: we assume there actually is a dislocation in the file provided :)

    # coordinates of the dislocation's core
    positions = data.particles.positions[data.particles['Dislocation'] != -1]

    core_x = np.mean(positions[:, 0])
    core_y = np.mean(positions[:, 1])

    w = data.cell[0, 0] # cell size in X direction
    h = data.cell[1, 1] # cell size in Y direction

    # finding max distance from dislocation's core to cell's edges
    # => (almost) all atoms in the cell will be inside the cylinder with radius r_max
    RADIUS_MAX = np.max([
        ( core_x**2       + core_y**2       ) ** 0.5,
        ( core_x**2       + (h - core_y)**2 ) ** 0.5,
        ( (w - core_x)**2 + core_y**2       ) ** 0.5,
        ( (w - core_x)**2 + (h - core_y)**2 ) ** 0.5
    ]) // RADIUS_STEP * RADIUS_STEP

    EXPR_LEFT = f'(Position.X - {core_x})^2 + (Position.Y - {core_y})^2'
    
    r = RADIUS_MIN
    out = {}
    
    print()
    print(f'Dislocation\'s core coordinates: ({core_x:.2f}, {core_y:.2f}).')
    print(f'Computing c_Mg for radiuses ranging from {RADIUS_MIN:.2f} to {RADIUS_MAX:.2f} stepping {RADIUS_STEP:.2f} per calculation.')
    print(f'Using expression: {EXPR_LEFT} < r^2. (variable "r")')
    print()

    while r <= RADIUS_MAX:

        # TODO: perhaps there are better ways to do this stuff

        expr = f'{EXPR_LEFT} < {r}^2'

        # selecting and counting Mg atoms
        sel_mod.expression = expr + ' && ParticleType == 2'
        data = pipeline.compute(last_frame)
        N_mg = np.sum(data.particles['Selection'])

        # selecting and counting all atoms
        sel_mod.expression = expr
        data = pipeline.compute(last_frame)
        N = np.sum(data.particles['Selection'])

        # calculating and saving Mg concentration
        c = N_mg / N
        out[r] = c

        # don't forget to iterate
        print(f'c({r:.2f})\t= {c:.4f}')
        r += RADIUS_STEP
    
    return out


if __name__ == '__main__':

    """
    STEP 0: parse script arguments

    getting input (dump) and output (csv) file names
    NOTE: other steps are in the process_dump function
    """

    parser = ArgumentParser(description='OVITO local solute saturation concentration in Cottrell atmospheres analysis.')

    parser.add_argument('-i', '--input', type=Path, help='relative path to the input LAMMPS dump file')
    parser.add_argument('-o', '--output', type=Path, help=f'output csv file name (filename only, without extension). Will be saved at ./{OUTPUT_DIR}')
    parser.add_argument('-v', '--vacancies', type=float, help='fraction of vacancies (not %%) for averaging')
    parser.add_argument('-t', '--temperature', type=int, help='temperature for averaging')

    args = parser.parse_args()

    # enabling averaging mode if all paramenets are given
    parameters = [args.vacancies, args.temperature]
    all_parameters_specified = all(list(map (lambda x: x is not None, parameters)))

    # error!
    if not all_parameters_specified and any(parameters):
        raise Exception('You specified only one parameter, both are needed.')

    # averaging mode
    if all_parameters_specified:
        param_str = f'{(args.vacancies * 100.0):g}vac_{int(args.temperature)}temp'

        if not args.output:
            # create directory for calculation results if it doesn't exist and save output there
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            args.output = OUTPUT_DIR / Path(param_str + '.csv')

        # rename with a number ("file_(n).csv") if file exists
        counter = 1
        while args.output.exists():
            args.output = args.output.with_name(args.output.stem.replace(f'_({counter - 1})', '') + f'_({counter}){args.output.suffix}')
            counter += 1

        all_data = {}

        for dumpfile in INPUT_DIR.glob(f'*{param_str}*'):
            for r, c in process_dump(dumpfile).items():
                if r in all_data.keys():
                    all_data[r].append(c)
                else:
                    all_data[r] = [c]

        for r in all_data.keys():
            all_data[r] = sum(all_data[r]) / len(all_data[r])

        with open(args.output, "w", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(['r', 'c'])
            writer.writerows(all_data.items())

    # default mode
    else:
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

        with open(args.output, "w", newline="") as csv_file:
            data = process_dump(str(args.input))

            writer = csv.writer(csv_file)
            writer.writerow(['r', 'c'])
            writer.writerows(data.items())

    print(f'\nOutput file: {args.output}')
