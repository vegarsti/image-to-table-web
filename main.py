import cv2
import sys
import pytesseract
from collections import namedtuple
import time
import statistics
import itertools
import csv

try:
    from PIL import Image
except ImportError:
    import Image

if len(sys.argv) != 3:
    print("Usage: python main.py [filename] [number_of_columns]")
    sys.exit()

filename = sys.argv[1]
image = cv2.imread(filename)
height, width, _ = image.shape  # assumes color image
picture_size = height * width

number_of_columns = int(sys.argv[2])
if number_of_columns < 1:
    print("Must have positive number of columns")
    sys.exit()

# image = Image.open(filename)

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
# print(boxes[0])

lefts = []
rights = []
tops = []
bottoms = []

for box in boxes:
    # print(box.left, box.right)
    lefts.append(box.left)
    rights.append(box.right)
    tops.append(box.top)
    bottoms.append(box.bottom)


def boxes_equal(b1, b2):
    equal_size = b1.size == b2.size
    equal_top = b1.top == b2.top
    return equal_size and equal_top


def is_box_to_right_of_line(box, x):
    return box.left > x


def is_box_inside_other_box(box1, box2):
    if boxes_equal(box1, box2):
        return False
    size = box1.size < box2.size
    left = box1.left >= box2.left
    right = box1.right <= box2.right
    top = box1.top >= box2.top
    bottom = box1.bottom <= box2.bottom
    return size and left and right and top and bottom


"""
cv2.imshow("Some title", image)
cv2.waitKey(0)
"""

sorted_boxes = sorted(boxes, key=lambda c: c.size, reverse=True)

number_of_lines = 0

lines = []

line_box = sorted_boxes[3]

show_all_boxes = False

for box_num, box in enumerate(sorted_boxes):
    count = True
    previous_box = sorted_boxes[box_num - 1]
    if boxes_equal(box, previous_box):
        count = False
    if box.size > 0.3 * picture_size:  # some threshold
        count = False
    if box.text.strip() == "" and count:
        number_of_lines += 1
        lines.append(box)
    if show_all_boxes:
        image = cv2.rectangle(
            image, (box.left, box.top), (box.right, box.bottom), (0, 255, 0), 2
        )
        cv2.imshow("title", image)
        cv2.waitKey(0)


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


all_divisions = []
line_dicts = []
for i, line_box in enumerate(lines):
    # find those boxes which are inside this line
    line_dict = {}
    line_dict["bounding_box"] = line_box
    word_boxes = []
    line_dict["words"] = []
    for box in sorted_boxes:
        if is_box_inside_other_box(box, line_box):
            word_boxes.append(box)
    line_dict["word_boxes"] = sorted(word_boxes, key=lambda word_box: word_box.left)
    line_dict["words"] = [word_box.text for word_box in line_dict["word_boxes"]]

    diffs = [
        line_dict["word_boxes"][i].left - line_dict["word_boxes"][i - 1].right
        for i in range(1, len(line_dict["word_boxes"]))
    ]

    indexes = find_index_of_n_largest(diffs, number_of_columns)
    group_words = []
    divisions = [
        (line_dict["word_boxes"][index].left, line_dict["word_boxes"][index - 1].right)
        for index in indexes
    ]
    all_divisions.append(divisions)
    for i, index in enumerate(indexes):
        if i == 0:
            start = 0
            end = indexes[i]
        else:
            start = indexes[i - 1]
            end = indexes[i]
        group = line_dict["words"][start:end]
        group_word = " ".join(group)
        group_words.append(group_word)
    group = line_dict["words"][end:]
    group_word = " ".join(group)
    group_words.append(group_word)

    line_dict["group_words"] = group_words

    line_dicts.append(line_dict)

sorted_lines = sorted(line_dicts, key=lambda l: l["bounding_box"].top)

all_midpoints = []
all_lefts = []
for divisions in all_divisions:
    midpoints = []
    lefts = []
    for left, right in divisions:
        midpoints.append(right + (left - right) / 2)
        lefts.append(left)
    all_midpoints.append(midpoints)
    all_lefts.append(lefts)

transposed_midpoints = list(zip(*all_midpoints))
transposed_lefts = list(zip(*all_lefts))

dividing_points = []
for column_midpoints in transposed_midpoints:
    dividing_points.append(int(max(column_midpoints)))


all_lists = []


def partition(items, predicate=bool):
    a, b = itertools.tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred), (item for pred, item in b if pred))


rows_strings = []
rows = []
for line_dict in sorted_lines:
    points_to_left = line_dict["word_boxes"]
    cells = []
    for i, dividing_point in enumerate(dividing_points):
        points_to_left, points_to_right = partition(
            points_to_left, lambda word_box: word_box.right > dividing_point
        )
        points_to_left = list(points_to_left)
        points_to_right = list(points_to_right)
        text = " ".join(p.text for p in points_to_left)
        text = text.replace(",", ".")
        cells.append(text)
        points_to_left = points_to_right
    cells.append(" ".join(p.text for p in points_to_left))
    rows_strings.append(",".join(cells))
    rows.append(cells)

filename_csv = filename.split(".")[0] + ".csv"
with open(filename_csv, "w") as csv_file:
    wr = csv.writer(csv_file, delimiter=",")
    for row in rows:
        wr.writerow(row)
