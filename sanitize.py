import re


def is_numerical(cell):
    N = len(cell)
    digits = "\d"
    N_numerical = len(re.findall(digits, cell))
    percentage_numerical = N_numerical / N
    return percentage_numerical > 0.5


def make_cell_numerical(cell, full_dictionary):
    regex_replace = dict((re.escape(k), v) for k, v in full_dictionary.items())
    pattern = re.compile("|".join(regex_replace.keys()))
    cleaned_cell = pattern.sub(lambda m: regex_replace[re.escape(m.group(0))], cell)
    return cleaned_cell


def sanitize(items):
    characters_to_remove = ["|", " "]
    remove_dictionary = {character: "" for character in characters_to_remove}
    replacement_dictionary = {"—": "-"}
    full_dictionary = {**replacement_dictionary, **remove_dictionary}
    new_items = []
    for cell in items:
        if len(cell) > 0 and is_numerical(cell):
            new_items.append(make_cell_numerical(cell, full_dictionary))
        else:
            new_items.append(cell)
    return new_items


def main():
    items = ["1 000", "1.000", "|100,", "Ny"]
    print(items)
    print(sanitize(items))
    print()


if __name__ == "__main__":
    main()
