from dataclasses import dataclass, field
from typing import List

# field(default_factory=make_french_deck)


@dataclass
class BoundingBox:
    height: int
    width: int
    left: int
    bottom: int
    text: str
    size: int = 0
    right: int = 0
    top: int = 0

    def __init__(self, height, width, left, bottom, text):
        self.height = height
        self.width = width
        self.left = left
        self.bottom = bottom
        self.text = text

        # Add dynamic fields
        self.size = height * width
        self.right = left + width
        self.top = bottom + height

    def __eq__(self, other):
        equal_size = self.size == other.size
        equal_top = self.top == other.top
        return equal_size and equal_top

    def inside(self, other):
        equal = self == other
        size = self.size < other.size
        left = self.left >= other.left
        right = self.right <= other.right
        top = self.top >= other.top
        bottom = self.bottom <= other.bottom
        return equal and size and left and right and top and bottom
