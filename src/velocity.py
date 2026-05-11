import os

from argparse import ArgumentParser
from pathlib import Path
from scipy.signal import savgol_filter

import pandas as pd
import matplotlib.pyplot as plt


if os.getcwd().endswith('src'): os.chdir('..')

INPUT_DIR = Path('results/mobility') # should already exist


if __name__ == '__main__':

    """
    STEP 0: parse script arguments
    """

    parser = ArgumentParser(description='OVITO dislocation mobility analysis: time-position, time-velocity data calculation and plotting.')

    parser.add_argument('-i', '--input', type=str, help='relative path to the input csv file')

    args = parser.parse_args()

    if not args.input:
        # get latest file in the directory
        input_file = max(filter(lambda x: x.is_file(), INPUT_DIR.iterdir()), key=lambda x: x.stat().st_mtime)
        print(f'Input file name was not provided, using latest csv file: {input_file}')
    else:
        input_file = args.input

    """
    STEP 1: calculate and plot given data
    """

    # [Ang] -> [m] => 1e-10
    # [ps] -> [s] => 1e-12
    # [Ang/ps] -> [m/s] => 1e-10/1e-12 = 1e2

    dt = 1.0
    timestep = 100

    with open('common.ini', 'r') as config:
        for line in config:
            if line.startswith('variable shear_run_timestep'):
                dt = float(line.split()[3]) # [ps]

            if line.startswith('variable shear_dump_freq'):
                timestep = int(line.split()[3]) # [frames] ig


    df = pd.read_csv(input_file)

    fig, (ax_tOx, ax_tOv) = plt.subplots(nrows=1, ncols=2)

    df['t'] *= dt # convert timesteps to real time [ps]

    df['v_raw'] = df['x'].diff() / df['t'].diff()

    df['v_savgol'] = savgol_filter(
        df['x'],
        window_length=51,
        polyorder=2,
        deriv=1,
        delta=dt * timestep
    )

    df['v_median'] = df['v_raw'].rolling(window=5, center=True).median()

    df['v_ewm'] = df['v_raw'].ewm(span=16, adjust=False).mean()

    # full velocity median
    median_velocity = df['v_raw'].median()

    print(f'Median velocity: {median_velocity:.4f} Ang/ps = {(median_velocity * 100.0):.4f} m/s')

    # (time, X-coordinate) plot
    df.plot(
        x='t',
        y='x',
        ax=ax_tOx,
        title='position [Ang] over time [ps]'
    )

    # (time, velocity) plot
    df.plot(
        x='t',
        y=[
            # 'v_raw',
            'v_savgol',
            # 'v_median',
            'v_ewm'
        ],
        ax=ax_tOv,
        title='velocity [Ang/ps] over time [ps]'
    )
    
    # velocity median
    ax_tOv.axhline(
        y=median_velocity,
        color='red',
        linestyle='--'
    )

    plt.tight_layout()
    plt.show()
