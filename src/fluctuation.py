import time
import os
import numpy as np

import pandas as pd
import matplotlib.pyplot as plt

from argparse import ArgumentParser
from pathlib import Path

from ovito.io import import_file
from ovito.modifiers import PolyhedralTemplateMatchingModifier, \
                            ExpressionSelectionModifier, \
                            DeleteSelectedModifier


if os.getcwd().endswith('src'): os.chdir('..')

OUTPUT_ROOT = Path('results/fluctuation') # will create if doesn't exist
PRINT_FREQ = 10

if __name__ == '__main__':

    parser = ArgumentParser(description='OVITO dislocation fluctuation analysis.')

    parser.add_argument('-i', '--input', type=str, required=True, help='relative path to the input directory (relative to .)')
    parser.add_argument('-o', '--output', type=str, help='relative path to the output directory (relative to ./results/fluctuation)')

    args = parser.parse_args()

    if not args.output:
        output_dir = OUTPUT_ROOT / Path(args.input).name
        print(f'Output directory name was not provided, using input directory name as such: {output_dir}')
    else:
        output_dir = args.output

    # create directory for analysis results
    output_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    fluctuations = {}

    for entry in Path(args.input).iterdir():
        # we want to process only .atom files
        if not entry.is_file or entry.suffix != '.atom':
            continue

        # NOTE: this part is straight up copied from position.py, so i shortened it a bit.
        #       see "position.py" for more comments and stuff

        # import file
        # LAMMPS dump columns: id x y z
        pipeline = import_file(entry, columns=[
            'Particle Identifier',
            'Position.X', 'Position.Y', 'Position.Z'
        ])

        pipeline.modifiers.append(ExpressionSelectionModifier(
            expression='Position.Y < CellSize.Y * 0.5 + %f && Position.Y > CellSize.Y * 0.5 - %f' % (16.0, 16.0)
        ))

        pipeline.modifiers.append(PolyhedralTemplateMatchingModifier(
            only_selected=True
        ))

        pipeline.modifiers.append(ExpressionSelectionModifier(
            expression='StructureType == "FCC" || Position.Y < CellSize.Y * 0.5 - %f || Position.Y > CellSize.Y * 0.5 + %f' % (10.0, 10.0)
        ))

        pipeline.modifiers.append(DeleteSelectedModifier())

        output_file = Path(output_dir) / Path(entry.stem + '.png')

        local_start_time = time.time()
        total_frames = pipeline.num_frames

        df = pd.DataFrame(columns=['t', 'x'])

        print(f'Analysing "{entry.name}".')
        print(f'Total frames to calculate: {total_frames}\n')

        for frame, data in enumerate(pipeline.frames):
            timestep = data.attributes['Timestep']
            positions = data.particles.positions[:, 0]

            core_x = np.mean(positions)

            if frame % PRINT_FREQ == 0:
                print(
                    f'X: {core_x:.4f}',
                    f'{frame}/{total_frames} ({(frame / total_frames * 100.0):.1f}%)',
                    f'{(time.time() - local_start_time):.2f} sec',
                    sep='\t|| '
                )
            
            # save row of data
            df = pd.concat(
                [df, pd.DataFrame([{'t': timestep, 'x': core_x}])], 
                ignore_index=True
            )

        df.plot(x='t', y='x', title='x(t)')

        plt.title('position [Ang] over time [ps]')
        plt.xlabel('time (t)')
        plt.ylabel('position (x)')
        plt.grid(True, linestyle='--', alpha=0.7)

        plt.savefig(
            output_file,
            dpi=300,
            bbox_inches='tight',
            facecolor='white',
            transparent=False
        )

        plt.close()

        spread = df['x'].max() - df['x'].min()
        fluctuations[entry.stem] = spread

        print(f'\nTime elapsed for "{entry.name}": {(time.time() - local_start_time):.2f} sec')
        print(f'Max spread: {spread}')
        print(f'Output plot: {output_file}\n')

    fluctuations_file = Path(output_dir) / Path('fluctuation.png')
    fluctuations_df = pd.DataFrame(columns=['entry', 'spread', 'perc'])

    fluctuations_df['entry'] = fluctuations.keys()
    fluctuations_df['spread'] = fluctuations.values()
    fluctuations_df['perc'] = list(map(lambda x: x[1] / (float(x[0].split('x')[0]) * 0.0405 / np.sqrt(2)), fluctuations.items()))

    fluctuations_df = fluctuations_df.sort_values('entry', key=lambda x: x.str.split('x').str[0].astype(int))

    fig, (ax_entry_spread, ax_entry_perc) = plt.subplots(nrows=2, ncols=1)

    fluctuations_df.plot(
        x='entry',
        y='spread',
        ax=ax_entry_spread,
        title='max fluctuation spread [Ang] by entry'
    )

    fluctuations_df.plot(
        x='entry',
        y='perc',
        ax=ax_entry_perc,
        title='max fluctuation spread (over max length, %) by entry'
    )

    plt.tight_layout()

    plt.savefig(
        fluctuations_file,
        dpi=300,
        bbox_inches='tight',
        facecolor='white',
        transparent=False
    )

    plt.close()

    print(f'Total time elapsed: {(time.time() - start_time):.2f} sec')
    print(f'Max fluctuations for each entry (plotted at {fluctuations_file}):')
    for row in fluctuations_df.itertuples(index=False, name=None):
        print(f'{row[0]}: {row[1]:.4f} ({row[2]:.2f}%)')
