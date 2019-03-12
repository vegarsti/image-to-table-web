from PIL import Image
import io


def square_image_no_fill(image):
    width = float(image.width)
    height = float(image.height)
    if width == height:
        return image
    if width > height:
        crop_size = int(height)
    else:
        crop_size = int(width)
    # left, upper, right, lower
    crop_tuple = (0, 0, crop_size, crop_size)
    image = image.crop(crop_tuple)
    return image


def thumbnail(image_data, N=800):
    image = Image.open(io.BytesIO(image_data))
    squared_image = square_image_no_fill(image)
    size = N, N
    squared_image.thumbnail(size)
    with io.BytesIO() as output:
        squared_image.save(output, format="PNG")
        image_contents = output.getvalue()
    return image_contents
