import pandas as pd
import numpy as np

dataPath = "R4_CurrentData.dat"
with open(dataPath, 'r') as file:
    for line in file.readline():
        # Should parse if either experiment info or data
        print(line)
