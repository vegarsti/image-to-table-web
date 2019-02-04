import cv2
import sys
import pytesseract
from collections import namedtuple, Counter
import time
import statistics
import itertools
import csv
import argparse
import pandas as pd
import numpy as np


def column_widths(table):
    """Get the maximum size for each column in table"""
    return [max(map(len, col)) for col in zip(*table)]


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


def pretty_print_table(table):
    number_of_columns = len(table[0])
    alignment_operators = {"left": "<", "right": ">"}
    alignment_subset = alignment_operators["left"] + alignment_operators["right"] * (
        number_of_columns - 1
    )
    justified_table = align_table(table, alignment_subset)
    padded_table = add_padding(justified_table, padding=1)
    lines = join_columns_with_divider(padded_table, decorator=" ")
    lines = right_strip_lines(lines)
    finished_output = join_formatted_lines(lines)
    print(finished_output)


def analyze(filepath, number_of_columns, show, from_flask=False):
    print(filepath)
    if from_flask:
        with open(filepath[1:], "rb") as file_descriptor:
            image_string = file_descriptor.read()
        image = cv2.imdecode(
            np.fromstring(image_string, np.uint8), cv2.IMREAD_UNCHANGED
        )
    else:
        try:
            image = cv2.imread(filepath)
        except FileNotFoundError:
            print("File not found!")
            sys.exit(1)

    print(f"Analyzing {filepath}.")
    # can add preprocessing steps here!
    height, width, _ = image.shape  # assumes color image
    picture_size = height * width

    if show:
        cv2.imshow(filepath, image)
        cv2.waitKey(0)

    fields_string = "level left top width height conf text"
    fields = fields_string.split()

    tesseract_config = "--psm 6 -l nor"  # assume a single uniform block of text
    data = pytesseract.image_to_data(
        image, config=tesseract_config, output_type=pytesseract.Output.DICT
    )

    for field, values in data.items():
        N = len(values)

    boxes = [{} for i in range(N)]
    for field, values in data.items():
        if field in fields:
            for i, value in enumerate(values):
                boxes[i][field] = value

    for box in boxes:
        box["right"] = box["left"] + box["width"]
        box["bottom"] = box["top"] + box["height"]
        box["size"] = box["width"] * box["height"]

    Box = namedtuple("Box", sorted(boxes[0]))
    boxes = [Box(**box) for box in boxes]
    levels = Counter(box.level for box in boxes)

    LINE_LEVEL = 4
    WORD_LEVEL = 5

    number_of_lines = levels[LINE_LEVEL]

    def find_index_of_n_largest(items, n):
        # assume items is sorted list with positive numbers of diffs
        indexes = []
        copied_items = [i for i in items]
        while len(indexes) < n - 1:
            max_index = copied_items.index(max(copied_items))
            indexes.append(max_index)
            copied_items = [i for i in copied_items]
            copied_items[max_index] = 0
        return sorted([i + 1 for i in indexes])

    def get_boxes_at_level(boxes, level):
        # return bounding boxes, sorted by pixel value of top of bounding box
        return sorted(
            [box for box in boxes if box.level == level], key=lambda box: box.top
        )

    boxes_bounding_lines = get_boxes_at_level(boxes, LINE_LEVEL)
    boxes_bounding_words = get_boxes_at_level(boxes, WORD_LEVEL)

    def boxes_equal(b1, b2):
        equal_size = b1.size == b2.size
        equal_top = b1.top == b2.top
        return equal_size and equal_top

    def is_box_inside_other_box(box1, box2):
        if boxes_equal(box1, box2):
            return False
        size = box1.size < box2.size
        left = box1.left >= box2.left
        right = box1.right <= box2.right
        top = box1.top >= box2.top
        bottom = box1.bottom <= box2.bottom
        return size and left and right and top and bottom

    def partition(items, predicate=bool):
        a, b = itertools.tee((predicate(item), item) for item in items)
        return (
            (item for pred, item in a if not pred),
            (item for pred, item in b if pred),
        )

    all_divisions = []
    line_dicts = []
    for i, line_box in enumerate(boxes_bounding_lines):
        # find those boxes which are inside this line
        line_dict = {}
        line_dict["bounding_box"] = line_box
        word_boxes = [
            box
            for box in boxes_bounding_words
            if is_box_inside_other_box(box, line_box)
        ]
        line_dict["word_boxes"] = sorted(word_boxes, key=lambda word_box: word_box.left)
        line_dict["words"] = [word_box.text for word_box in line_dict["word_boxes"]]

        # Find horizontal pixel difference between words
        diffs = [
            line_dict["word_boxes"][i].left - line_dict["word_boxes"][i - 1].right
            for i in range(1, len(line_dict["word_boxes"]))
        ]

        if number_of_columns > 1:
            indexes = find_index_of_n_largest(diffs, number_of_columns)
            group_words = []
            divisions = [
                (
                    line_dict["word_boxes"][index].left,
                    line_dict["word_boxes"][index - 1].right,
                )
                for index in indexes
            ]
            line_dict["divisions"] = divisions
            all_divisions.append(divisions)
        line_dicts.append(line_dict)

    if number_of_columns > 1:
        all_midpoints = []
        for divisions in all_divisions:
            midpoints = []
            for left, right in divisions:
                midpoints.append(right + (left - right) / 2)
            all_midpoints.append(midpoints)

        transposed_midpoints = list(zip(*all_midpoints))

        dividing_points = []
        for column_midpoints in transposed_midpoints:
            dividing_points.append(int(max(column_midpoints)))

    rows_strings = []
    rows = []
    sorted_line_dicts = sorted(line_dicts, key=lambda l: l["bounding_box"].top)
    for line_dict in sorted_line_dicts:
        points_to_left = line_dict["word_boxes"]
        cells = []
        if number_of_columns > 1:
            for i, dividing_point in enumerate(dividing_points):
                points_to_left, points_to_right = partition(
                    points_to_left, lambda word_box: word_box.right > dividing_point
                )
                points_to_left = list(points_to_left)
                points_to_right = list(points_to_right)
                text = " ".join(p.text for p in points_to_left)
                text = text.replace(",", ".")  # ugly hack!
                cells.append(text)
                points_to_left = points_to_right
            cells.append(" ".join(p.text for p in points_to_left))
            comma_separated_row = ",".join(cells)
            rows_strings.append(comma_separated_row)
        else:  # 1 column
            cell = " ".join(p.text for p in points_to_left)
            cells = [cell]
            rows_strings.append(cell)
        rows.append(cells)

    # Write output
    print("Printing table.")
    print()
    pretty_print_table(rows)
    print()

    # Write to files
    parent_directory, _, filename_with_ending = filepath.rpartition("/")
    filename_without_ending, _, _ = filename_with_ending.rpartition(".")
    if parent_directory:
        parent_parent, _, _ = parent_directory.rpartition("/")
        if parent_parent:
            prefix = f"{parent_parent}/"
        else:
            prefix = ""
        csv_path = f"{prefix}csvs/{filename_without_ending}.csv"
        excel_path = f"{prefix}excel_files/{filename_without_ending}.xlsx"
    else:
        csv_path = f"{filename_without_ending}.csv"
        excel_path = f"{filename_without_ending}.xlsx"

    # Write to csv file
    print(f"Writing csv file {csv_path}.")
    with open(csv_path, "w+") as csv_file:
        wr = csv.writer(csv_file, delimiter=",")
        for row in rows:
            wr.writerow(row)

    print(f"Writing excel file {excel_path}.")
    df = pd.read_csv(csv_path, header=None)
    df.to_excel(excel_path, header=None, index=False)

    return df
