import argparse
import sys
from api import analyze

try:
    from PIL import Image
except ImportError:
    import Image

parser = argparse.ArgumentParser(
    description="Extract tabular data from an image using Tesseract OCR.",
    prog=sys.argv[0],
)


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

analyze(filepath=args.filepath, number_of_columns=args.columns, show=args.show)
