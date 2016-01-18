import os
import mimetypes
import subprocess
from PIL import Image

from collections import namedtuple


FileInfo = namedtuple('FileInfo', ['format', 'width', 'height', 'units'])


def get_dimensions(path, format='PDF', width=0, height=0, units='pt'):
    """
    Takes a document path and tests to see if it can extract dimensions from
    the document itself. Will return default width and height on failure.
    """
    if os.path.exists(path):
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type == 'application/pdf':
            # Handle PDFs differently to images. There may be multiple pages
            # but just use the first to get the dimensions.
            # identify reliably interprets rotation
            width, height = subprocess.check_output([
                "identify", "-format", "%Wx%H,", path
            ]).split(",")[0].strip().split("x")
            width = int(width)
            height = int(height)
        else:
            # Try to open the image and extract its properties
            try:
                image = Image.open(path)
            except IOError:
                pass
            else:
                format = image.format
                # image.size is a tuple of (width, height)
                width = image.size[0]
                height = image.size[1]
                units = 'px'
    return FileInfo(format, width, height, units)
