import base64
import itertools
import json
import statistics
import sys
from collections import namedtuple, Counter

import cv2
import numpy as np
import pandas as pd
import pytesseract
import os
from dotenv import load_dotenv

load_dotenv()
ON_COMPUTER = os.getenv("ON_COMPUTER")
if not ON_COMPUTER == "1":
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
import scipy.ndimage as snd

from sanitize import sanitize


def image_to_base64_json(filepath):
    try:
        with open(filepath, "rb") as file_descriptor:
            image_string = file_descriptor.read()
    except FileNotFoundError:
        print("File not found!")
        sys.exit(1)
    base64_encoded_image = base64.b64encode(image_string)
    image_json = {"base64_image": base64_encoded_image}
    return image_json


def resize_image(image_as_byte_array):
    image = cv2.imdecode(image_as_byte_array, cv2.IMREAD_COLOR)
    height, width, _ = image.shape
    factor = min(1, float(1024.0 / width))
    new_size = int(factor * width), int(factor * height)
    cv2.resize(image, new_size, interpolation=cv2.INTER_CUBIC)
    resized_image_as_byte_array = cv2.imencode(".png", image)[1].tostring()
    return resized_image_as_byte_array


def resize_json_wrapper(image_json):
    base64_encoded_image = image_json.get("base64_image")
    language = image_json.get("language")
    image_string = base64.b64decode(base64_encoded_image)
    image_as_byte_array = np.frombuffer(image_string, np.uint8)
    resized_image_as_byte_array = resize_image(image_as_byte_array)
    base64_encoded_resized_image = base64.b64encode(resized_image_as_byte_array)
    image_json["base64_image"] = base64_encoded_resized_image


def tesseract_specific_code(image_json):
    base64_encoded_image = image_json.get("base64_image")
    language = image_json.get("language")
    image_string = base64.b64decode(base64_encoded_image)
    image_as_byte_array = np.frombuffer(image_string, np.uint8)
    image = cv2.imdecode(image_as_byte_array, cv2.IMREAD_UNCHANGED)
    language_map = {"Norwegian": "nor", "English": "eng"}
    language_config = language_map[language]
    tesseract_config = (
        f"--psm 6 -l {language_config}"
    )  # assume a single uniform block of text
    data = pytesseract.image_to_data(
        image, config=tesseract_config, output_type=pytesseract.Output.DICT
    )
    print(pytesseract.image_to_string(image, config=tesseract_config))
    data["shape"] = image.shape
    return json.dumps(data)


def find_index_of_n_largest(items, n):
    # assume items is sorted list with positive numbers of diffs
    indexes = []
    copied_items = [i for i in items]
    while len(indexes) < n - 1:
        if len(copied_items) == 0:
            break
        else:
            max_index = copied_items.index(max(copied_items))
            indexes.append(max_index)
            copied_items = [i for i in copied_items]
            copied_items[max_index] = 0
    return sorted([i + 1 for i in indexes])


def get_boxes_at_level(boxes, level):
    # return bounding boxes, sorted by pixel value of top of bounding box
    return sorted([box for box in boxes if box.level == level], key=lambda box: box.top)


def boxes_equal(b1, b2):
    equal_size = b1.size == b2.size
    equal_top = b1.top == b2.top
    return equal_size and equal_top


def is_box_inside_other_box(box1, box2):
    size = box1.size <= box2.size
    left = box1.left >= box2.left
    right = box1.right <= box2.right
    top = box1.top >= box2.top
    bottom = box1.bottom <= box2.bottom
    return size and left and right and top and bottom


def partition(items, predicate=bool):
    a, b = itertools.tee((predicate(item), item) for item in items)
    return ((item for pred, item in a if not pred), (item for pred, item in b if pred))


def analyze(image_json, number_of_columns):
    # preprocessing steps, e.g., reshaping
    image_json = resize_json_wrapper(image_json)
    # end preprocessing

    data = json.loads(tesseract_specific_code(image_json))
    height, width, _ = data.pop("shape", None)  # assumes color image

    boxes = create_box_objects_from_tesseract_bounding_boxes(data)

    should_sanitize = True

    levels = Counter(box.level for box in boxes)
    LINE_LEVEL = 4
    WORD_LEVEL = 5

    ## SHOULD FIX SOMETHING HERE

    boxes_bounding_lines = get_boxes_at_level(boxes, LINE_LEVEL)
    boxes_bounding_words = get_boxes_at_level(boxes, WORD_LEVEL)

    all_divisions = []
    line_dicts = []
    for i, line_box in enumerate(boxes_bounding_lines):
        line_dict = find_boxes_inside_line(boxes_bounding_words, line_box)
        diffs = find_horizontal_distances_between_bounding_boxes(line_dict)
        if number_of_columns > 1:
            indexes = find_index_of_n_largest(diffs, number_of_columns)
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
        dividing_points = find_all_dividing_points(all_divisions)
    else:
        dividing_points = []
    rows_strings = []
    rows = []
    sorted_line_dicts = sorted(line_dicts, key=lambda l: l["bounding_box"].top)
    all_distances = []
    for i in range(number_of_columns):
        all_distances.append([])
    right_points = dividing_points
    for j, line_dict in enumerate(sorted_line_dicts):
        boxes_to_left = line_dict["word_boxes"]
        cells = []
        if number_of_columns > 1:
            left_point = 0
            for i, right_point in enumerate(right_points):
                boxes_to_left, boxes_to_right = partition(
                    boxes_to_left, lambda word_box: word_box.right > right_point
                )
                boxes_to_left = list(
                    sorted(list(boxes_to_left), key=lambda box: box.right)
                )
                boxes_to_right = list(
                    sorted(list(boxes_to_right), key=lambda box: box.right)
                )
                if len(boxes_to_left) > 0:
                    left_point_ = boxes_to_left[-1].right
                    first_left_point = boxes_to_left[0].left
                else:
                    left_point_ = 0
                    first_left_point = 0
                distance_to_right = right_point - left_point_
                distance_to_left = first_left_point - left_point
                distances = (distance_to_left, distance_to_right)
                all_distances[i].append(distances)
                text = " ".join(p.text for p in boxes_to_left)
                cells.append(text)
                boxes_to_left = boxes_to_right
                left_point = right_point
            right_point = width
            if len(boxes_to_left) > 0:
                distance_to_right = right_point - boxes_to_left[-1].right
                distance_to_left = boxes_to_left[0].left - left_point
            else:
                distance_to_right = right_point
                distance_to_left = 0
            distances = (distance_to_left, distance_to_right)
            all_distances[(number_of_columns - 1)].append(distances)
            cells.append(" ".join(p.text for p in boxes_to_left))
            comma_separated_row = ",".join(cells)
            rows_strings.append(comma_separated_row)
        else:  # 1 column
            cell = " ".join(p.text for p in boxes_to_left)
            cells = [cell]
            rows_strings.append(cell)
        if should_sanitize:
            sanitized_cells = sanitize(cells)
        else:
            sanitized_cells = cells
        rows.append(sanitized_cells)
    """
    if number_of_columns > 1:
        alignment_list = find_column_alignments(all_distances)
    elif number_of_columns == 1:
        alignment_list = ["left"]
    """

    df = pd.DataFrame(rows, columns=None)
    df_json = df.to_json(orient="split")
    return {"df": df_json}  # "alignment_list": alignment_list}


def create_box_objects_from_tesseract_bounding_boxes(data):
    fields_string = "level left top width height conf text"
    fields = fields_string.split()
    for field, values in data.items():
        N = len(values)
    boxes = [{} for _ in range(N)]
    for field, values in data.items():
        if field in fields:
            for i, value in enumerate(values):
                boxes[i][field] = value
    for box in boxes:
        box["right"] = box["left"] + box["width"]
        box["bottom"] = box["top"] + box["height"]
        box["size"] = box["width"] * box["height"]
    example_box = boxes[0]
    Box = namedtuple("Box", sorted(example_box))
    boxes = [Box(**box) for box in boxes]
    return boxes


def find_boxes_inside_line(boxes_bounding_words, line_box):
    line_dict = {}
    line_dict["bounding_box"] = line_box
    word_boxes = [
        box for box in boxes_bounding_words if is_box_inside_other_box(box, line_box)
    ]
    line_dict["word_boxes"] = sorted(word_boxes, key=lambda word_box: word_box.left)
    line_dict["words"] = [word_box.text for word_box in line_dict["word_boxes"]]
    return line_dict


def find_horizontal_distances_between_bounding_boxes(line_dict):
    diffs = [
        line_dict["word_boxes"][i].left - line_dict["word_boxes"][i - 1].right
        for i in range(1, len(line_dict["word_boxes"]))
    ]
    return diffs


def find_all_dividing_points(all_divisions):
    all_midpoints = []
    for divisions in all_divisions:
        midpoints = []
        for left, right in divisions:
            midpoints.append(right)
        all_midpoints.append(midpoints)
    transposed_midpoints = list(zip(*all_midpoints))
    dividing_points = []
    for column_midpoints in transposed_midpoints:
        dividing_points.append(int(max(column_midpoints)))
    return dividing_points


def find_column_alignments(all_distances):
    alignment_list = []
    for i, column_distances in enumerate(all_distances):
        left, right = [
            [distances_in_row[i] for distances_in_row in column_distances]
            for i in range(2)
        ]
        this_column_orientation = min(
            ("left", statistics.stdev(left)),
            ("right", statistics.stdev(right)),
            key=lambda t: t[1],
        )[0]
        alignment_list.append(this_column_orientation)
    return alignment_list


def write_to_files(df_json, filepath):
    df = pd.read_json(df_json, orient="split")
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
    print(f"Writing csv file {csv_path}.")
    df.to_csv(csv_path, header=None, index=False)
    print(f"Writing excel file {excel_path}.")
    df.to_excel(excel_path, header=None, index=False)


def find_number_of_columns(image_json, show=False):
    base64_encoded_image = image_json.get("base64_image")
    image_string = base64.b64decode(base64_encoded_image)
    image_as_byte_array = np.frombuffer(image_string, np.uint8)
    image = cv2.imdecode(image_as_byte_array, cv2.IMREAD_UNCHANGED)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    x_axis_sum = np.sum(gray, axis=0)
    sum_image_height = 50
    sum_image = np.zeros((sum_image_height, *x_axis_sum.shape))
    sum_image[:] = x_axis_sum
    cv2.normalize(sum_image, sum_image, 0, 255, cv2.NORM_MINMAX)
    sum_image = sum_image.astype(np.uint8)
    # sum_image = cvh.normalize(sum_image).astype(np.uint8)
    sum_image = cv2.resize(sum_image, (400, 50), interpolation=cv2.INTER_CUBIC)
    # sum_image = cvh.resize(sum_image, shape=(50, 400)) # Kommer snart :)

    if show:
        import matplotlib.pyplot as plt

        plt.figure()
        plt.imshow(sum_image)

    eroded = snd.grey_opening(sum_image, 11)

    if show:
        plt.figure()
        plt.imshow(eroded)

    _, otsu = cv2.threshold(eroded, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # otsu = cvh.threshold_otsu(eroded)
    dilated_otsu = cv2.dilate(otsu, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    # otsu = cvh.dilate(otsu, 3)
    # eroded = cv.erode(otsu, cv.getStructuringElement(cv.MORPH_RECT, (35, 35)))
    if show:
        fig, (ax1, ax2) = plt.subplots(1, 2)
        ax1.imshow(gray)
        ax2.imshow(dilated_otsu)
        plt.show()
    dilated = dilated_otsu
    dilated = dilated[0]
    first_black = np.argmin(dilated)
    last_black = dilated.shape[0] - np.argmin(dilated[::-1])
    # clip
    dilated = dilated[first_black:last_black]
    diffed = np.diff(dilated)
    num_changes = np.count_nonzero(diffed)
    num_columns = (num_changes + 2) // 2
    return num_columns
