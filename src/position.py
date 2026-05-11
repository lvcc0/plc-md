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

PRINT_FREQ = 10   # printing in the main loop
INVIS_THRESH = 16 # "invisibility frames" after periodic adjustment in case of fluctuating on the edge


if __name__ == '__main__':

    """
    STEP 0: parse script arguments

    getting input (dump) and output (csv) file names
    """

    parser = ArgumentParser(description='OVITO dislocation mobility analysis: time-position relation csv output.')

    parser.add_argument('-i', '--input', type=str, help='relative path to the input LAMMPS dump file')
    parser.add_argument('-o', '--output', type=str, help='output csv file name (filename only, without extension). Will be saved at ./results/mobility')

    args = parser.parse_args()

    if not args.input:
        # get latest file in the directory
        input_file = max(filter(lambda x: x.is_file(), INPUT_DIR.iterdir()), key=lambda x: x.stat().st_mtime)
        print(f'Input file name was not provided, using latest dump file: {input_file}')
    else:
        input_file = args.input
    
    # create directory for calculation results if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # if output file name is not provided, make it "input_file.stem".csv and place it in ./results/mobility
    output_file = args.output if args.output else Path(input_file).stem + '.csv'
    output_file = OUTPUT_DIR / Path(output_file)

    # rename with a number ("file_(n).csv") if file exists
    counter = 1
    while output_file.exists():
        output_file = output_file.with_name(output_file.stem.replace(f'_({counter - 1})', '') + f'_({counter}){output_file.suffix}')
        counter += 1

    """
    STEP 1: isolate dislocation structure

    with the use of the following modifiers we are getting non-FCC atom structures,
    so we can leave out only dislocation (basically the only non-FCC) structure.
    """

    # import file
    # LAMMPS dump columns: id x y z
    pipeline = import_file(input_file, columns=[
        'Particle Identifier',
        'Position.X', 'Position.Y', 'Position.Z'
    ])

    # 1. selecting middle horizontal layer of the cell for PTM to calculate faster (limiting calculation zone)
    #    we assume that the dislocation is in the middle for this to work
    zone_selection_mod = ExpressionSelectionModifier(
        expression='Position.Y < CellSize.Y * 0.5 + %f && Position.Y > CellSize.Y * 0.5 - %f' % (16.0, 16.0)
    )
    pipeline.modifiers.append(zone_selection_mod)

    # 2. add PTM modifier to highlight non-FCC parts of the cell structure (dislocation)
    ptm_mod = PolyhedralTemplateMatchingModifier(
        only_selected=True
    )
    pipeline.modifiers.append(ptm_mod)

    # 3. select unwanted atoms
    selection_mod = ExpressionSelectionModifier(
        expression='StructureType == "FCC" || Position.Y < CellSize.Y * 0.5 - %f || Position.Y > CellSize.Y * 0.5 + %f' % (10.0, 10.0)
    )
    pipeline.modifiers.append(selection_mod)

    # 4. delete selected atoms
    delete_mod = DeleteSelectedModifier()
    pipeline.modifiers.append(delete_mod)

    """
    STEP 2: get dislocation position at each moment of time and save each frame data in an external csv file for further analysis
    """
    
    start_time = time.time()
    total_frames = pipeline.num_frames

    # initial data
    data_init = pipeline.compute(0)
    positions_init = data_init.particles['Position'][:, 0]
    core_spread_init = np.max(positions_init) - np.min(positions_init)

    lx = data_init.cell[0, 0] # cell's X-length 
    ix = 0                    # imaging coefficient (to move dislocation's atoms ix * lx to the right after periodic adjustments)
    
    periodic_flag = False # was there a periodic adjustment?
    invis_frames = 0

    print(f'Total frames to calculate: {total_frames}\n')

    with open(output_file, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(['t', 'x'])

        # NOTE: "timesteps" are not actual "time elapsed" but calculation steps,
        #       so for actual physical time you should see "timestep" command in
        #       input LAMMPS script that generated used dump input file.

        # NOTE: this loop structure automatically computes each frame
        for frame, data in enumerate(pipeline.frames):
            timestep = data.attributes['Timestep']       # current frame timestep
            positions = data.particles_.positions_[:, 0] # all atom X-coordinates (modifiable/mutable)
            
            core_spread = np.max(positions) - np.min(positions)

            # take periodic movement into account
            # only account for periodic adjustment if it wasn't accounted for in the previous INVIS_THRESH frames
            if not invis_frames:
                # "if dislocation is visually split in two because of the periodic movement"
                if np.any(positions < core_spread_init * 2.0) and core_spread > core_spread_init * 2.0:
                    if not periodic_flag:
                        periodic_flag = True

                    # move all the atoms that "teleported" to the left one lx to the right (make dislocation structure whole)
                    positions[positions < core_spread_init * 2.0] = positions[positions < core_spread_init * 2.0] + lx

                # when periodic adjustments are finished, we increment our imaging coefficient
                # (for we have moved one whole cell to the right, basically)
                if np.all(positions < core_spread_init * 2.0) and periodic_flag:
                    ix += 1
                    periodic_flag = False

                    # initiate invisibility for a few frames
                    invis_frames = INVIS_THRESH

            core_x = np.mean(positions) + ix * lx

            # decrement "invisibility frames"
            if invis_frames:
                invis_frames -= 1

            if frame % PRINT_FREQ == 0:
                print(
                    f'X: {core_x:.4f}',
                    f'{frame}/{total_frames} ({(frame / total_frames * 100.0):.1f}%)',
                    f'{(time.time() - start_time):.2f} sec',
                    sep='\t|| '
                )

            writer.writerow([timestep, core_x])

    print(f'\nTotal time elapsed: {(time.time() - start_time):.2f} sec')
    print(f'Output file: {output_file}')
