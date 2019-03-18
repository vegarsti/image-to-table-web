import argparse
import sys
import pandas as pd
import base64
import cv2
import numpy as np
from api import analyze, image_to_base64_json, write_to_files

try:
    from PIL import Image
except ImportError:
    import Image

parser = argparse.ArgumentParser(
    description="Extract tabular data from an image using Tesseract OCR.",
    prog=sys.argv[0],
)


def column_widths(table):
    """Get the maximum size for each column in table"""
    string_table = [[str(s) for s in row] for row in table]
    return [max(map(len, col)) for col in zip(*string_table)]


def copy_nested_list(l):
    """Return a copy of list l to one level of nesting"""
    return [list(i) for i in l]


def align_table(table, align):
    """Return table justified according to align"""
    widths = column_widths(table)
    new_table = copy_nested_list(table)
    for row in new_table:
        for cell_num, cell in enumerate(row):
            row[cell_num] = "{:{align}{width}}".format(
                cell, align=align[cell_num], width=widths[cell_num]
            )
    return new_table


def add_padding(table, padding):
    """Return a version of table which is padded according to inputted padding"""
    new_table = copy_nested_list(table)
    for i, row in enumerate(new_table):
        padding_string = " " * padding
        for j, cell in enumerate(row):
            left = padding_string
            right = padding_string
            if j == 0:
                left = ""
            elif j == len(row) - 1:
                right = ""
            new_table[i][j] = left + new_table[i][j] + right
    return new_table


def join_columns_with_divider(table, decorator):
    """Join each line in table with the decorator string between each cell"""
    return [decorator.join(row) for row in table]


def right_strip_lines(lines):
    """Remove trailing spaces on each line"""
    return [line.rstrip() for line in lines]


def join_formatted_lines(lines):
    """Return the finished output"""
    return "\n".join(lines)


def pretty_print_table(table, alignment_list):
    alignment_operators = {"left": "<", "right": ">"}
    alignment_options = [alignment_operators[alignment] for alignment in alignment_list]
    justified_table = align_table(table, alignment_options)
    padded_table = add_padding(justified_table, padding=1)
    lines = join_columns_with_divider(padded_table, decorator=" ")
    lines = right_strip_lines(lines)
    finished_output = join_formatted_lines(lines)
    print(finished_output)


def show_image(image_json):
    base64_encoded_image = image_json.get("base64_image")
    image_string = base64.b64decode(base64_encoded_image)
    image_as_byte_array = np.fromstring(image_string, np.uint8)
    image = cv2.imdecode(image_as_byte_array, cv2.IMREAD_UNCHANGED)
    cv2.imshow("Image", image)
    cv2.waitKey(0)


def positive_integer(n):
    """Parse positive integer, possibly raising error"""
    message = "must be a positive integer"
    try:
        n = int(n)
    except ValueError:
        raise argparse.ArgumentTypeError(message)
    if n > 0:
        return n
    else:
        raise argparse.ArgumentTypeError(message)


parser.add_argument("filepath", type=str, help="path to image file")
parser.add_argument("columns", type=positive_integer, help="number of columns")
parser.add_argument("--show", action="store_true", help="show all bounding boxes")
args = parser.parse_args()

image_json = image_to_base64_json(args.filepath)
language = "English"
image_json["language"] = language
analyzed_results = analyze(image_json=image_json, number_of_columns=args.columns)
df_json = analyzed_results["df"]
alignment_list = analyzed_results["alignment_list"]
df = pd.read_json(df_json, orient="split")
rows = df.values.tolist()

print("Printing table.")
print()
pretty_print_table(rows, alignment_list)
print()
write_to_files(df_json, args.filepath)
