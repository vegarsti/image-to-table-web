import sys
import subprocess

arguments = sys.argv[1:]
if len(arguments) % 2 != 0:
    print("Every file needs a specified number of columns.")
    print("Usage: [filename_1] [columns_1] [filename_2] [columns_2] ...")
filenames = arguments[::2]
columns = arguments[1::2]
print(filenames)
print(columns)

for filename, column in zip(filenames, columns):
    subprocess.run(f"python main.py {filename} {column}")
    print()
