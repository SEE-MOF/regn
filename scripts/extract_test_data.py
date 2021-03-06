import glob
import os
import numpy as np
import tqdm
from calendar import monthrange
from regn.data import create_output_file, extract_data
import argparse

################################################################################
# Command line arguments.
################################################################################

parser = argparse.ArgumentParser(description='Extract test data')
parser.add_argument('input', metavar='input', type=str, nargs=1,
                    help='Path to input data.')
parser.add_argument('n_samples', metavar='n', type=int, nargs=1,
                    help='How many samples to extract from each file.')
parser.add_argument('output', metavar="output", type=str, nargs=1,
                    help='Filename for output file.')

args = parser.parse_args()
data_path = args.input[0]
samples = args.n_samples[0]
output = args.output[0]

################################################################################
# Extract data.
################################################################################

months = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
years = [14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 15, 15]

file = create_output_file(output)
for y, m in zip(years, months):
    _, n_days = monthrange(2000 + y, m)
    days = np.arange(1, 3)
    print("Processing {}/{}".format(y, m))
    for d in tqdm.tqdm(days):
        extract_data(data_path, y, m, d, samples, file)
file.close()
