# -*- coding: utf-8 -*-
"""
Created on Sat May 17 22:24:05 2025

@author: Bjorn and small adjustments were made by Victor
"""

import pandas as pd
import numpy as np
import re
from itertools import zip_longest

with open(r"C:\Users\v12vi\Downloads\cura_manier_4.27.gcode", 'r') as file:
    gcode_lines = file.readlines()
gcode = pd.Series([line.strip() for line in gcode_lines]) 

UV_hop_Z = 0.4 #mm
UV_hop_Y = 2.3 #mm
UV_hop_X = 40.3 #mm

# Find the first layer after the skirt is printed
index_layer1 = gcode[gcode.str.contains("LAYER:1")].index.min()
m140_index = gcode[gcode.str.contains('M140 S0')].index.min()

# Create series with only the data after "LAYER:1"
gcode_start = gcode.iloc[:index_layer1]
gcode_finish = gcode.iloc[m140_index:]
gcode_layer1 = gcode.iloc[index_layer1:m140_index]

# Obtain all the indices where only T1 and T0 are found
T1_indices_check = gcode_layer1[gcode_layer1 == 'T1'].index.tolist()
T0_indices_check = gcode_layer1[gcode_layer1 == 'T0'].index.tolist()

T1_indices = [x - index_layer1 for x in T1_indices_check]
T0_indices = [x - index_layer1 for x in T0_indices_check]

# Create lists of series between T1 and T0, and T0 and T1
T1_series = []
T0_series = []

for T1_index, T0_index in zip(T1_indices, T0_indices[1:] + [len(gcode_layer1)]):
    new_series = gcode_layer1.iloc[T1_index:T0_index]
    T1_series.append(new_series)

# Safe concatenation of T1_series
if T1_series:
    T1_series_concat = pd.concat(T1_series, ignore_index=True)
    T1_series_concat1 = pd.concat(T1_series, ignore_index=False)
else:
    T1_series_concat = pd.Series(dtype=object)
    T1_series_concat1 = pd.Series(dtype=object)

T1_series = T1_series[:-1]

Z_indices_series = T1_series_concat1[
    T1_series_concat1.str.contains('Z') & (T1_series_concat1.str.len() > 1)
].index
LAYER_indices = T1_series_concat1[
    T1_series_concat1.str.contains('LAYER') & (T1_series_concat1.str.len() > 1)
].index

Z_indices_list = []
for series in T1_series:
    Z_indices = [index for index, element in enumerate(series) if re.search(r'Z', str(element))]
    Z_indices_list.append(Z_indices)

for T0_index, T1_index in zip(T0_indices, T1_indices):
    new_series = gcode_layer1.iloc[T0_index:T1_index]
    T0_series.append(new_series)

# Find all the Z indices in the T1 series concatenation
T1_indices_concat = [i for i, value in enumerate(T1_series_concat) if value == 'T1']
Z_indices_concat = [i for i, value in enumerate(T1_series_concat) if 'Z' in value]

T1_copies = []
for start_index, end_index in zip(Z_indices_concat, Z_indices_concat[1:] + [None]):
    new_series = T1_series_concat.iloc[start_index + 1:end_index]
    if len(new_series) >= 10:
        T1_copies.append(new_series)

gcode_last_part = []

if T0_indices_check and T1_indices_check:
    if max(T0_indices_check) > max(T1_indices_check):
        gcode_last_part = gcode.iloc[T0_indices_check[-1]:]
    else:
        T1_series.append(gcode.iloc[T1_indices_check[-1]:])

lamp_module1 = [pd.concat([pd.Series(['M42 P124 S255']), s], ignore_index=True) for s in T1_copies]
lamp_module = [pd.concat([s, pd.Series(['M42 P124 S0'])], ignore_index=True) for s in lamp_module1]

lamp_module_noE = []
for series in lamp_module:
    new_series = pd.Series(dtype=object)
    for value in series.values:
        if value.startswith(';'):
            new_series = pd.concat([new_series, pd.Series([value])], ignore_index=True)
        else:
            modified_value = value.split('E')[0]
            new_series = pd.concat([new_series, pd.Series([modified_value])], ignore_index=True)
    lamp_module_noE.append(new_series)

def add_value_to_Y(y_series, value_to_add):
    if y_series.isna().any():
        return y_series
    updated_y_series = y_series.apply(lambda y_string: re.sub(
        r'Y(\d+(\.\d+)?)', 
        lambda match: f'Y{float(match.group(1)) + value_to_add:.5f}', 
        y_string))
    return updated_y_series

def add_value_to_Z(z_series, value_to_add):
    if z_series.isna().any():
        return z_series
    updated_z_series = z_series.apply(lambda z_string: re.sub(
        r'Z(\d+(\.\d+)?)', 
        lambda match: f'Z{float(match.group(1)) + value_to_add:.5f}', 
        z_string))
    return updated_z_series

def add_value_to_X(x_series, value_to_add):
    if x_series.isna().any():
        return x_series
    updated_x_series = x_series.apply(lambda x_string: re.sub(
        r'X(\d+(\.\d+)?)', 
        lambda match: f'X{float(match.group(1)) + value_to_add:.5f}', 
        x_string))
    return updated_x_series

Y_hop = [add_value_to_Y(y, UV_hop_Y) for y in lamp_module_noE]
Z_hop = [add_value_to_Z(z, UV_hop_Z) for z in Y_hop]
UV_series = [add_value_to_X(x, UV_hop_X) for x in Z_hop]

T1_split = []
T1_split1 = []

for series in T1_series:
    new_series = pd.Series(dtype='object')
    layer_found = False
    for line in series:
        if ';MESH:NONMESH' in line:
            layer_found = True
            if len(new_series) > 0:
                T1_split.append(new_series)
            new_series = pd.Series(dtype='object')
        else:
            new_series = pd.concat([new_series, pd.Series([line])], ignore_index=True)
    if layer_found and len(new_series) > 0:
        T1_split.append(new_series)

for series in T1_series:
    new_series = pd.Series(dtype='object')
    layer_found = False
    for i, line in enumerate(series):
        if ';LAYER' in line:
            layer_found = True
            start_index = max(0, i - 4)
            end_index = i + 1
            new_series = series.iloc[start_index:end_index].reset_index(drop=True)
            if not new_series.empty:
                T1_split1.append(new_series)
    if layer_found and not new_series.empty:
        T1_split1.append(new_series)

layer_indices = []
for series in T1_series:
    indices = series.index[series.str.contains(';LAYER')].tolist()
    layer_indices.extend(indices)

layer_indices1 = [index - 4 for series in T1_series for index in series.index[series.str.contains(';LAYER')].tolist()]

# Safe concat for T1_split
if T1_split:
    T1_split_concat = pd.concat(T1_split, ignore_index=True)
else:
    T1_split_concat = pd.Series(dtype=object)

t1_uv = [pd.concat([t, u], ignore_index=True) for t, u in zip(T1_split, UV_series)]

concatenated_series = []
i = 0
while i < len(t1_uv):
    current_series = t1_uv[i]

    if not current_series.empty and current_series.iloc[0] == 'T1':
        while i + 1 < len(t1_uv) and (t1_uv[i + 1].empty or t1_uv[i + 1].iloc[0] != 'T1'):
            i += 1
            current_series = pd.concat([current_series, t1_uv[i]], ignore_index=True)
        concatenated_series.append(current_series)
    else:
        concatenated_series.append(current_series)
    i += 1

t1_uv = concatenated_series

min_length = min(len(T0_series), len(t1_uv))

interleaved_series = [series for pair in zip(T0_series[:min_length], t1_uv[:min_length]) for series in pair]

if len(t1_uv) > len(T0_series):
    interleaved_series += t1_uv[min_length:]

# Safe concat for interleaved_series
if interleaved_series:
    interleaved_series_all = pd.concat(interleaved_series, ignore_index=True)
else:
    interleaved_series_all = pd.Series(dtype=object)

gcode_final = pd.concat([gcode_start, interleaved_series_all, gcode_finish], ignore_index=True)

gcode_final.to_csv('Python 14.gcode', index=False, header=False)
