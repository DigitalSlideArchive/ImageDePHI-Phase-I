# pip install pyyaml pytesseract large-image
# apt-get install tesseract-ocr

import argparse
import io
import itertools
import json
import logging
import os
import sys

import PIL.Image
import PIL.ImageOps
import pytesseract
import yaml

import large_image

user_patterns = """TCGA-\\n\\n-\\n\\n\\n\\n-\\d\\d\\n-\\d\\d-\\n\\n\\d
TCGA-\\n\\n-\\n\\n\\n\\n-\\d\\d\\n
"""

# This could be something like '--psm 11 --oem 1'
open('/tmp/tesseract.patterns', 'w').write(user_patterns)
tesseract_config = '--user-patterns /tmp/tesseract.patterns'
# tesseract_config = None


def get_text_from_image(image):
    words = {}
    options = {}
    for crop, rotate, contrast in itertools.product(
            (0, 1, 2),
            (None, PIL.Image.ROTATE_90, PIL.Image.ROTATE_180, PIL.Image.ROTATE_270),
            (None, 'autocontrast', 'equalize'),
            ):
        subimage = PIL.ImageOps.crop(image, crop)
        if rotate:
            subimage = subimage.transpose(rotate)
        if contrast:
            subimage = getattr(PIL.ImageOps, contrast)(subimage)
        text = pytesseract.image_to_string(subimage, config=tesseract_config).strip()
        text = text.replace('"', ' ').replace("'", ' ').replace('|', ' ').replace('@', '0')
        if not text.strip():
            continue
        key = (crop, rotate, contrast)
        options[key] = ' '.join(text.split())
        # if len(text.strip()):
        #     print(crop, str(rotate)[:1], str(contrast)[:1],
        #           ' '.join(text.split()))
        for word in text.split():
            words[word] = words.get(word, []) + [key]
    if not(words):
        return ''
    while len(options) > 1 and len(words):
        _, word, wopts = sorted((-len(val), word, val) for word, val in words.items())[0]
        words.pop(word, None)
        for w in list(words):
            words[w] = [wopt for wopt in words[w] if wopt in wopts]
            if not len(words[w]):
                words.pop(w)
        options = {k: v for k, v in options.items() if k in wopts}
    return next(iter(options.values()))


def ocr_images(args):  # noqa
    meta = {}
    if args.collection and os.path.exists(args.collection):
        meta = json.load(open(args.collection))
    for src in args.source:
        if args.verbose:
            sys.stderr.write('%s\n' % src)
            sys.stderr.flush()
        try:
            ts = large_image.open(src)
        except Exception:
            continue
        filename = os.path.basename(src)
        for key in ts.getAssociatedImagesList():
            try:
                image, _ = ts.getAssociatedImage(key)
            except Exception:
                pass
            image = PIL.Image.open(io.BytesIO(image))
            if False:
                text = pytesseract.image_to_string(image, config=tesseract_config).strip()
                text = ' '.join(text.split())
            else:
                text = get_text_from_image(image)
            if text:
                meta.setdefault(filename, {})
                if meta[filename].get(key) != text:
                    meta[filename][key] = (
                        meta[filename][key] + '\n' if key in meta[filename] else '') + text
                if args.verbose >= 2:
                    sys.stderr.write('  %s: %s\n' % (key, text))
                    sys.stderr.flush()
    if args.out:
        outptr = open(args.out, 'w')
    else:
        outptr = sys.stdout
    outptr.write(yaml.dump(meta))
    if args.collection:
        meta = json.dump(meta, open(args.collection, 'w'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='OCR all associated images from files that can be opened with large_image.')
    parser.add_argument(
        'source', nargs='+', help='Source file.')
    parser.add_argument(
        '--collection',
        help='A file path to read and write collected data.  Use this to '
        'merge multiple runs of the program.')
    parser.add_argument(
        '--out',
        help='If specified, output the results to this text file.  Otherwise, '
        'output to stdout.')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase output.')
    logger = logging.getLogger('large_image')
    logger.setLevel(1000)
    args = parser.parse_args()
    ocr_images(args)
