import pandas as pd
from pathlib import Path
import re
from typing import Iterable
import math

#code made by Friso, our good friend chatGPT helped with the debugging
#code made for BEP group to change the intensity of the UV lamp.

PIN = 124
START = 255  # pin number to match in M42 command
OUTFILE = "uv_curing_10.2_faded.gcode"
pattern = rf"^M42\s+P{PIN}\s+S(?:[1-9]\d*)\s*$"   # regex, anchor to full line


# read every line into a single-column DataFrame
df = pd.read_csv("uv_curing_10.2.gcode",
    header=None,            # no header row
    names=["line"],         # name the single column
    engine="python",        # needed when sep is regex/newline
) 

mask    = df["line"].str.match(pattern)
idxs    = df.index[mask]   
N       = len(idxs)
new_S = [math.floor(START * (N - i) / N) for i in range(N)]

for new_val, row in zip(new_S, idxs):
    # substitute ONLY the *first* S<number> in that row
    df.at[row, "line"] = re.sub(r"S\d+", f"S{new_val}", df.at[row, "line"], count=1)

with open(OUTFILE, "w", encoding="utf-8", newline="") as f:
    f.write("\n".join(df["line"]))
    f.write("\n")                 # final newline (just like the slicer adds)

print(f"Done ➜ {OUTFILE}")

print(new_S)
print(N)