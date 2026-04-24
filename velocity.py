from argparse import ArgumentParser
from scipy.signal import savgol_filter

import pandas as pd
import matplotlib.pyplot as plt

if __name__ == '__main__':

    """
    STEP 0: parse script arguments
    """

    # TODO: nice description
    parser = ArgumentParser(description='something something dislocation speed')

    # TODO: helps
    parser.add_argument('-i', '--input', type=str, required=True, help='')
    parser.add_argument('-s', '--save', action='store_true', help='')

    args = parser.parse_args()

    """
    STEP 1: calculate and plot given data
    """

    # [Ang] -> [m] => 1e-10
    # [ps] -> [s] => 1e-12
    # [Ang/ps] -> [m/s] => 1e-10/1e-12 = 1e2 = 100

    dt = 1.0

    with open('common.ini', 'r') as config:
        for line in config:
            if line.startswith('variable shear_run_timestep'):
                dt = float(line.split()[3]) # [ps]

    df = pd.read_csv(args.input)

    fig, (ax_tOx, ax_tOv) = plt.subplots(nrows=1, ncols=2)

    df['t'] *= dt # convert timesteps to real time [ps]

    df['v_raw'] = df['x'].diff() / df['t'].diff()

    df['v_savgol'] = savgol_filter(
        df['x'],
        window_length=51,
        polyorder=2,
        deriv=1,
        delta=dt * 100.0
    )

    df['v_median'] = df['v_raw'].rolling(window=5, center=True).median()

    df['v_ewm'] = df['v_raw'].ewm(span=16, adjust=False).mean()

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
    
    plt.tight_layout()
    plt.show()
