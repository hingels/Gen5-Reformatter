#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 28 00:08:47 2023

@author: henryingels
"""

import pandas as pd
import numpy as np
from os import makedirs
from os.path import join, dirname

paths_path = "./paths.md"
datapath, instructions_path = None, None
with open(paths_path) as file:
    for line in file:
        split = line.split(':')
        name = split[0].strip()
        path = ':'.join(split[1:]).strip()
        if name == "reformat.md":
            instructions_path = path
        elif name == "Input Excel file":
            datapath = path
assert (datapath and instructions_path) is not None

num_of_measurements = 0
found_actualTemperature = False
columnNumbers = None
rowLetters = []
start_index = None
measurements = []
for i, (row_name, line) in enumerate(pd.read_excel(datapath).iterrows()):
    if line.iloc[0] == "Actual Temperature:":
        found_actualTemperature = True
        num_of_measurements += 1
        measurements.append([])
    elif found_actualTemperature:
        if columnNumbers is None:
            if line.iloc[2] == 1:
                columnNumbers = np.array([int(item) for item in line.iloc[2:] if np.isnan(item) == False])
            continue
        if start_index is None:
            start_index = i
        if type(letter := line.iloc[1]) is str:
            rowLetters.append(letter)
        measurement_index = (i - start_index) % num_of_measurements
        measurements[measurement_index].append(line.iloc[2:(2+len(columnNumbers))])

folder = dirname(datapath)
folder = join(folder, "Reformatted")
makedirs(folder, exist_ok = True)

def melt(dataframe, id_vars = "Row", var_name = "Column", value_name = "Value"):
    melted = dataframe.reset_index().melt(id_vars = id_vars, var_name = var_name, value_name = value_name)
    not_nan = (melted["Value"].isna() == False)
    melted = melted[not_nan]
    return melted
def melt_multiple(dataframe_list):
    for dataframe in dataframe_list:
        yield melt(dataframe)


for i, rows in enumerate(measurements):
    measurement = pd.DataFrame(data = np.array(rows), index = pd.Index(rowLetters, name = "Row"), columns = columnNumbers)
    measurements[i] = measurement


measurements_names = [None]*num_of_measurements
column_names = dict()
columns_represent = None
mode = None
mode_names = ["Measurements", "Columns", "Groups"]
def split_numbered(string):
    split = line.split('.')
    number, remainder = split[0], '.'.join(split[1:]).strip()
    assert number.isdigit()
    number = int(number)
    return number, remainder
def split_lettered(string):
    split = line.split('.')
    letters, remainder = split[0], '.'.join(split[1:]).strip()
    return letters.split(','), remainder
def parse_letterNumber(string):
    for i, letter in enumerate(string):
        if letter.isdigit(): break
    return string[0:i], int(string[i:])
replacements = []
with open(instructions_path) as instructions:
    for line in instructions:
        line = line.strip()
        if line == '': continue
        if line in mode_names:
            mode = line
            continue
        if mode == "Measurements":
            number, name = split_numbered(line)
            measurements_names[number - 1] = name
        elif mode == "Columns":
            if line.startswith("Represent"):
                columns_represent = line.removeprefix("Represent ")
                continue
            number, name = split_numbered(line)
            if name == r"\skip": continue
            column_names[number] = name
        elif mode == "Groups":
            if line.startswith("Use"):
                split = line.removeprefix("Use ").split(" instead of ")
                assert len(split) == 2
                new, old = split
                new = [parse_letterNumber(item) for item in new.split(',')]
                old = [parse_letterNumber(item) for item in old.split(',')]
                replacements.extend(zip(new, old))
nan = float('nan')
with open(instructions_path) as instructions:
    for line in instructions:
        line = line.strip()
        if line == '': continue
        if line in mode_names:
            mode = line
            continue
        if mode == "Groups":
            if line.startswith("Use"): continue
            letters, name = split_lettered(line)
            for i, measurement in enumerate(measurements):
                selection = measurement.loc[letters]
                for replacement in replacements:
                    new_index, old_index = replacement
                    try:
                        selection.loc[old_index]
                    except KeyError:
                        continue
                    selection.loc[old_index] = measurement.loc[new_index]
                melted = melt(selection)
                melted_names = [column_names[item] for item in melted["Column"] if item in column_names]
                column_traits = [None]*len(melted_names)
                for j, item in enumerate(melted_names):
                    if r'\trait' in item:
                        split = item.split(r'\trait')
                        melted_names[j] = split[0]
                        column_traits[j] = split[1]
                melted = pd.concat([
                    pd.Series([letters.index(item)+1 for item in melted["Row"]], name = "Row name (subsample)"),
                    pd.Series(melted_names, name = "Column name" + (columns_represent is not None)*f" (represents {columns_represent})"),
                    pd.Series(column_traits, name = "Column trait"),
                    melted
                ], axis = 1)
                melted.to_csv(join(folder, f"{name}_{measurements_names[i]}_longFormat.csv"), index = None)

for i, measurement in enumerate(measurements):
    measurement.rename_axis(None).to_excel(join(folder, f"{measurements_names[i]}.xlsx"))

for i, melted in enumerate(melt_multiple(measurements)):
    melted.to_csv(join(folder, f"{measurements_names[i]}_longFormat.csv"), index = None)
