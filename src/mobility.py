import time
import csv
import os
import numpy as np

from argparse import ArgumentParser
from pathlib import Path

from ovito.io import import_file
from ovito.modifiers import PolyhedralTemplateMatchingModifier, \
                            ExpressionSelectionModifier, \
                            DeleteSelectedModifier


if os.getcwd().endswith('src'): os.chdir('..')

INPUT_DIR = Path('dumps/shears')      # should already exist
OUTPUT_DIR = Path('results/mobility') # will create if doesn't exist

PRINT_FREQ = 10          # printing in the main loop
CORE_SPREAD_THRESH = 3.0 # dislocation spread after which we consider it split in two by the periodic movement


if __name__ == '__main__':

    """
    STEP 0: parse script arguments

    getting input (dump) and output (csv) file names
    """

    parser = ArgumentParser(description='OVITO dislocation mobility analysis: time-position relation csv output.')

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
    STEP 1: isolate dislocation structure

    with the use of the following modifiers we are getting non-FCC atom structures,
    so we can leave out only dislocation (basically the only non-FCC) structure.
    """

    print(f'Importing file: {args.input}')

    # import file
    # LAMMPS dump columns: id x y z
    pipeline = import_file(args.input, columns=[
        'Particle Identifier',
        'Position.X', 'Position.Y', 'Position.Z'
    ])

    # 1. selecting middle horizontal layer of the cell for PTM to calculate faster (limiting calculation zone)
    #    we assume that the dislocation is in the middle for this to work
    pipeline.modifiers.append(ExpressionSelectionModifier(
        expression='Position.Y < CellSize.Y * 0.5 + %f && Position.Y > CellSize.Y * 0.5 - %f' % (16.0, 16.0)
    ))

    # 2. add PTM modifier to highlight non-FCC parts of the cell structure (dislocation)
    pipeline.modifiers.append(PolyhedralTemplateMatchingModifier(
        only_selected=True
    ))

    # 3. select unwanted atoms
    pipeline.modifiers.append(ExpressionSelectionModifier(
        expression='StructureType == "FCC" || Position.Y < CellSize.Y * 0.5 - %f || Position.Y > CellSize.Y * 0.5 + %f' % (10.0, 10.0)
    ))

    # 4. delete selected atoms
    pipeline.modifiers.append(DeleteSelectedModifier())

    """
    STEP 2: get dislocation position at each moment of time and save each frame data in an external csv file for further analysis
    """

    start_time = time.time()
    total_frames = pipeline.num_frames

    # initial data
    data_init = pipeline.compute(0)

    lx = data_init.cell[0, 0] # cell's X-Length
    ix = 0                    # Imaging coefficient (to move dislocation's atoms ix*lx to the right after periodic adjustments)
    txl = lx * 0.33           # periodic adjustment Threshold (Left)
    txr = lx - txl            # periodic adjustment Threshold (Right)

    init_positions = data_init.particles.positions[:, 0]
    core_spread_init = np.max(init_positions) - np.min(init_positions)

    flag = False # have we started the periodic adjustment?

    print(f'Total frames to calculate: {total_frames}\n')

    with open(args.output, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['t', 'x'])

        # this loop structure automatically computes every frame
        for frame, data in enumerate(pipeline.frames):
            timestep = data.attributes['Timestep']       # current frame timestep
            positions = data.particles_.positions_[:, 0] # all atom X-coordinates (modifiable/mutable)

            # --- periodic adjustment part --- #

            # atoms are divided in two parts
            if np.max(positions) - np.min(positions) > core_spread_init * CORE_SPREAD_THRESH:
                if not flag: flag = True

            # periodic adjustment is on, move atoms that passed the edge one lx to the right
            if flag:
                positions[positions < txr] += lx

            # all the atoms have passed the edge fully, no fluctuations ahead.
            if flag and positions.min() > txl and positions.max() < txr:
                flag = False
                ix += 1

            # --- adjusted successfully (hopefully) --- #

            # actual dislocation position that we save
            core_x = np.mean(positions) + ix * lx

            if frame % PRINT_FREQ == 0:
                print(
                    f'X: {core_x:.4f}',
                    f'{frame}/{total_frames} ({(frame / total_frames * 100.0):.1f}%)',
                    f'{(time.time() - start_time):.2f} sec',
                    sep='\t|| '
                )

            writer.writerow([timestep, core_x])

    # NOTE: "timesteps" are not actual "time elapsed" but calculation steps,
    #       so for actual physical time you should see "timestep" command in
    #       input LAMMPS script that generated used dump input file.

    # NOTE: this algorithm works (in theory) only if lx (cell's X-length) > 3 dislocation lengths/spreads AT LEAST
    #       as it uses thresholds of lx/3 for periodic adjustment detection and consideration and stuff:
    #
    #                cell
    #       +--------------------+
    #       |                    |
    #       |     txl    txr     |
    #       | lx/3 | lx/3 | lx/3 |
    #       |                    |
    #       +--------------------+
    #       \   --->  lx  <---   /

    print(f'\nTotal time elapsed: {(time.time() - start_time):.2f} sec')
    print(f'Output file: {args.output}')
