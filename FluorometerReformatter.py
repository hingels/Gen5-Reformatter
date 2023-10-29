#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 28 00:08:47 2023

@author: henryingels
"""

import pandas as pd
import numpy as np
from os import path, makedirs

datapath = "/Volumes/Lab Drive/231023 DiI and DiO in liposomes/Fewer wells selected.xlsx"
instructions_path = "/Volumes/Lab Drive/231023 DiI and DiO in liposomes/reformat.md"

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

folder = path.dirname(datapath)
folder = path.join(folder, "Reformatted")
makedirs(folder, exist_ok = True)
for i, rows in enumerate(measurements):
    measurement = pd.DataFrame(data = np.array(rows), index = pd.Index(rowLetters, name = "Row"), columns = columnNumbers)
    measurements[i] = measurement
    print(measurement)
    measurement.rename_axis(None).to_excel(path.join(folder, f"Measurement_{i+1}.xlsx"))

def melt(dataframe, id_vars = "Row", var_name = "Column", value_name = "Value"):
    melted = dataframe.reset_index().melt(id_vars = id_vars, var_name = var_name, value_name = value_name)
    not_nan = (melted["Value"].isna() == False)
    melted = melted[not_nan]
    return melted
def melt_multiple(dataframe_list):
    for dataframe in dataframe_list:
        yield melt(dataframe)
for i, melted in enumerate(melt_multiple(measurements)):
    melted.to_csv(path.join(folder, f"Measurement_{i+1}_longFormat.csv"), index = None)


measurements_names = np.zeros((num_of_measurements, 1), dtype = object)
# column_names = np.zeros((len(columnNumbers), 1), dtype = object)
column_names = [None]*len(columnNumbers)
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
        if line in mode_names:
            mode = line
            continue
        if mode == "Measurements":
            number, name = split_numbered(line)
            measurements_names[number - 1] = name
        elif mode == "Columns":
            number, name = split_numbered(line)
            if name == r"\skip": continue
            column_names[number - 1] = name
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
        if line in mode_names:
            mode = line
            continue
        if mode == "Groups":
            if line.startswith("Use"): continue
            letters, name = split_lettered(line)
            for i, measurement in enumerate(measurements):
                selection = measurement.loc[letters]
                print(selection)
                for replacement in replacements:
                    new_index, old_index = replacement
                    try:
                        selection.loc[old_index]
                    except KeyError:
                        continue
                    selection.loc[old_index] = measurement.loc[new_index]
                print(selection.index)
                selection = selection.rename(
                    # index = {letter: j+1 for j, letter in enumerate(letters)},
                    columns = {j: f"{j}: {column_names[j]}" for j in range(len(columnNumbers))} )
                print(selection.index)
                selection.index.name = "Subsample"
                melted = melt(selection, id_vars = "Subsample", var_name = "Column", value_name = "Value")
                melted.to_csv(path.join(folder, f"{name}_Measurement_{i+1}_longFormat.csv"), index = None)
