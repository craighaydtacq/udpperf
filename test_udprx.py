import subprocess
import os

import sys

print(os.getcwd())
sys.path.append(os.getcwd())

# %%
subprocess.call("python udprx.py -R 40 -p 53676 --spp 20 --ssb 448 -c 96")

# %%
subprocess.call("python udptx.py -p 53676 -s 8960")
# %%
