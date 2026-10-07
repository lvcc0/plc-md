# TODO: include final time in the plot

import os

from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


if os.getcwd().endswith('src'): os.chdir('..')

INPUT_DIR = Path('results/lc')


if __name__ == '__main__':

    """
    STEP 0: parse script arguments
    """

    parser = ArgumentParser(description='TODO :)')

    parser.add_argument('-i', '--input', type=str, help='relative path to the input csv file')
    parser.add_argument('-s', '--save', type=bool, help='save to png (true) or show immediately (false)')

    args = parser.parse_args()

    if not args.input:
        # get latest file in the directory
        args.input = max(filter(lambda x: x.is_file(), INPUT_DIR.iterdir()), key=lambda x: x.stat().st_mtime)
        print(f'Input file name was not provided, using latest csv file: {args.input}')

    """
    STEP 1: plot given data
    """

    df = pd.read_csv(args.input)

    plt.plot(df['r'], df['c'], marker='o')
    plt.title('Local solute concentration VS Area radius', fontsize=14)
    plt.xlabel('$r$', fontsize=12)
    plt.ylabel('$c_{Mg}(r)$', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)

    plt.tight_layout()

    if args.save:
        # NOTE: please do not use ".csv" in file name, i don't want to make it harder :)
        plt.savefig(str(args.input).replace('.csv', '.png'))
    else:
        plt.show()
