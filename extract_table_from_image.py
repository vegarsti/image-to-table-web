import pytesseract
from pytesseract import Output
import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.filters import threshold_mean, threshold_otsu, try_all_threshold
import re
import sys


def convert_text_to_table(table_text):
    table_lines = table_text.split("\n")
    table = []
    for line in table_lines:
        table.append(line.split())
    return table


def add_bounding_boxes_to_image(image, boxes):
    # see https://stackoverflow.com/questions/20831612/getting-the-bounding-box-of-the-recognized-words-using-python-tesseract
    # draw the bounding boxes on the image
    """
    number_of_boxes = len(data["level"])
    for i in range(number_of_boxes):
        x, y, w, h = (
            data["left"][i],
            data["top"][i],
            data["width"][i],
            data["height"][i],
        )
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    """
    height, width, _ = image.shape  # assumes color image
    for b in boxes.splitlines():
        _, b1, b2, b3, b4, _ = b.split(" ")
        image = cv2.rectangle(
            image,
            (int(b1), height - int(b2)),
            (int(b3), height - int(b4)),
            (0, 255, 0),
            2,
        )
    return image


def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])


def threshold(image):
    thresh = threshold_otsu(image)
    binary = image > thresh

    fig, axes = plt.subplots(ncols=2, figsize=(8, 3))
    ax = axes.ravel()

    ax[0].imshow(image, cmap=plt.cm.gray)
    ax[0].set_title("Original image")

    ax[1].imshow(binary, cmap=plt.cm.gray)
    ax[1].set_title("Result")

    for a in ax:
        a.axis("off")

    plt.show()


def remove_consecutive_whitespace(s):
    # or ' '.join(s.split())
    return re.sub(" +", " ", s)


# filename = "table2.png"
filename = "images/larger-table.png"
img = cv2.imread(filename)

tesseract_config = "--psm 6"  # assume a single uniform block of text
image_text = pytesseract.image_to_string(img, config=tesseract_config)
table_text = remove_consecutive_whitespace(image_text.replace("|", ""))
print(table_text)
cv2.imshow(filename, img)
cv2.waitKey(0)
# print(convert_text_to_table(table_text))
boxes = pytesseract.image_to_boxes(img, config=tesseract_config)
# data = pytesseract.image_to_data(img, config=tesseract_config, output_type=Output.DICT)
# print(data.keys())
# print(boxes)
# show annotated image and wait for keypress
img = add_bounding_boxes_to_image(img, boxes)
cv2.imshow(filename, img)
cv2.waitKey(0)


def canny():
    import imageio
    from skimage import feature
    from skimage.filters import threshold_mean
    import numpy as np
    import matplotlib.pyplot as plt
    from PIL import Image, ImageEnhance, ImageFilter

    def rgb2gray(rgb):
        return np.dot(rgb[..., :3], [0.299, 0.587, 0.114])

    im = rgb2gray(imageio.imread("table.png"))
    thresh = threshold_mean(im)
    binary = im > thresh
    im = binary
    cv2.imshow()

    # config="outputbase digits"))

    # Compute the Canny filter for two values of sigma
    edges1 = feature.canny(im)
    edges2 = feature.canny(im, sigma=3)

    # display results
    fig, (ax1, ax2, ax3) = plt.subplots(
        nrows=1, ncols=3, figsize=(8, 3), sharex=True, sharey=True
    )

    ax1.imshow(im, cmap=plt.cm.gray)
    ax1.axis("off")
    ax1.set_title("noisy image", fontsize=20)

    ax2.imshow(edges1, cmap=plt.cm.gray)
    ax2.axis("off")
    ax2.set_title("Canny filter, $\sigma=1$", fontsize=20)

    ax3.imshow(edges2, cmap=plt.cm.gray)
    ax3.axis("off")
    ax3.set_title("Canny filter, $\sigma=3$", fontsize=20)

    fig.tight_layout()

    plt.show()
