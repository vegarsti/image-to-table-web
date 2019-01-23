import cv2
import sys
import pytesseract
from collections import namedtuple
import time

try:
    from PIL import Image
except ImportError:
    import Image

if len(sys.argv) != 3:
    print("Usage: python main.py [filename] [number_of_columns]")
    sys.exit()

filename = sys.argv[1]
image = cv2.imread(filename)

number_of_columns = int(sys.argv[2])
if number_of_columns < 1:
    print("Must have positive number of columns")
    sys.exit()

# image = Image.open(filename)

fields_string = "level left top width height conf text"
fields = fields_string.split()

tesseract_config = "--psm 6"  # assume a single uniform block of text
data = pytesseract.image_to_data(
    image, config=tesseract_config, output_type=pytesseract.Output.DICT
)
for field, values in data.items():
    # print(field)
    N = len(values)

characters = [{} for i in range(N)]
for field, values in data.items():
    if field in fields:
        for i, value in enumerate(values):
            characters[i][field] = value

for character in characters:
    character["right"] = character["left"] + character["width"]
    character["bottom"] = character["top"] + character["height"]
    character["size"] = character["width"] * character["height"]

Character = namedtuple("Character", sorted(characters[0]))
characters = [Character(**character) for character in characters]
# print(characters[0])

lefts = []
rights = []
tops = []
bottoms = []

for character in characters:
    # print(character.left, character.right)
    lefts.append(character.left)
    rights.append(character.right)
    tops.append(character.top)
    bottoms.append(character.bottom)

# print(sorted(lefts))
# print(sorted(rights))
# print()
# print(sorted(tops))
# print(sorted(bottoms))

left_diffs = []
for i, _ in enumerate(lefts):
    if i == 0:
        continue
    left_diffs.append(lefts[i] - lefts[i - 1])

right_diffs = []
for i, _ in enumerate(rights):
    if i == 0:
        continue
    right_diffs.append(rights[i] - rights[i - 1])

"""
print()
print(left_diffs)
print(right_diffs)
"""


def boxes_equal(b1, b2):
    equal_size = b1.size == b2.size
    equal_top = b1.top == b2.top
    return equal_size and equal_top


def is_character_to_right_of_line(character, x):
    return character.left > x


def is_box_inside_other_box(box1, box2):
    if boxes_equal(box1, box2):
        return False
    size = box1.size < box2.size
    left = box1.left >= box2.left
    right = box1.right <= box2.right
    top = box1.top >= box2.top
    bottom = box1.bottom <= box2.bottom
    return size and left and right and top and bottom


left_column = []
right_column = []

tentative_dividing_x = 400

for character in characters:
    if is_character_to_right_of_line(character, tentative_dividing_x):
        right_column.append(character)
    else:
        left_column.append(character)

# print(len(left_column))
# print(len(right_column))

for r in right_column:
    pass
    # print(r.text)

for l in left_column:
    pass
    # print(l.text)

for i, character in enumerate(characters):
    pass
    # print(character.text, i)


def character_distance(c1, c2):
    x = min(abs(c2.left - c1.right), abs(c1.left - c2.right))
    y = min(abs(c2.top - c1.bottom), abs(c1.top - c2.bottom))
    return x ** 2 + y ** 2


def find_nearest_character(character, characters):
    # assume non-overlapping
    return min(characters, key=lambda c: character_distance(character, c))


def calculate_box_size(character):
    return character.width * character.height


# print()

i = 4
character = characters[i]
near = find_nearest_character(character, characters)
# print(character.text)
# print(near.text)

"""
cv2.imshow("Some title", image)
cv2.waitKey(0)
"""

height, width, _ = image.shape  # assumes color image

sorted_boxes = sorted(characters, key=lambda c: c.size, reverse=True)

number_of_lines = 0

lines = []

line_box = sorted_boxes[3]

show_all_boxes = False

for box_num, box in enumerate(sorted_boxes):
    count = True
    if box_num == 0:  # entire image
        count = False
    previous_box = sorted_boxes[box_num - 1]
    if box_num == 1:  # table
        count = False
    # print("height: ", box.height)
    # print("width: ", box.width)
    # print("top: ", box.top)
    if boxes_equal(box, previous_box):
        count = False
    if box.text.strip() == "" and count:
        # print(box_num)
        number_of_lines += 1
        # print(box.left, box.top)
        # print(box.right, box.bottom)
        # print()
        lines.append(box)
    if show_all_boxes:
        image = cv2.rectangle(
            image, (box.left, box.top), (box.right, box.bottom), (0, 255, 0), 2
        )
        cv2.imshow("title", image)
        cv2.waitKey(0)

    """
    if box_num > 3 and is_box_inside_other_box(box, line_box):
        image = cv2.rectangle(
            image, (box.left, box.top), (box.right, box.bottom), (0, 255, 0), 2
        )
        cv2.imshow("title", image)
        cv2.waitKey(0)
    """

# print(number_of_lines)

# print()
# print()

line_dicts = []


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

    if line_dict["words"][0] == "John":
        print(line_dict["word_boxes"])

    indexes = find_index_of_n_largest(diffs, number_of_columns)
    # print(indexes)
    # time.sleep(5)
    group_words = []
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
for line in sorted_lines:
    print(",".join(line["group_words"]))
