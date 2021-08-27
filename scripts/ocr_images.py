# pip install pyyaml pytesseract large-image psutil
# apt-get install tesseract-ocr

import argparse
import concurrent.futures
import io
import itertools
import json
import logging
import multiprocessing
import os
import re
import sys
import time

import large_image
import PIL.Image
import PIL.ImageOps
import psutil
import pytesseract
import yaml

logger = logging.getLogger('large_image')
logger.setLevel(logging.CRITICAL)

start_time = time.time()

# \c - alpha (regex [a-zA-Z], except adds unicode)
# \d - digit (regex \d)
# \n - digit or alpha (regex \w)
# \p - punctuation (regex [^\w\s])
# \a - lower alpha (regex [a-z], but unicode)
# \A - upper alpha (regex [A-Z], but unicode)
# \* can repeat previous character (regex *)
user_patterns = """TCGA-\\n\\n-\\n\\n\\n\\n-\\d\\d\\n-\\d\\d-\\n\\n\\d
TCGA-\\n\\n-\\n\\n\\n\\n-\\d\\d\\n
\\d\\d/\\d\\d/\\d\\d
\\d/\\d\\d/\\d\\d
\\d\\d/\\d/\\d\\d
\\d/\\d/\\d\\d
"""

tesseractToRe = [
    ('\\c', r'[a-zA-Z]'),
    ('\\d', r'\d'),
    ('\\n', r'\w'),
    ('\\p', r'[^\w\s]'),
    ('\\a', r'[a-Z]'),
    ('\\A', r'[A=Z]'),
    ('\\*', r'\w'),
]
re_patterns = []
for pat in user_patterns.split('\n'):
    if pat.strip():
        pat = re.escape(pat.strip())
        for tpat, rpat in tesseractToRe:
            pat = pat.replace(re.escape(tpat), rpat)
        re_patterns.append(pat)
re_patterns = re.compile(r'(' + '|'.join(re_patterns) + r')')


# This could be something like '--psm 11 --oem 1'
open('/tmp/tesseract.patterns', 'w').write(user_patterns)
tesseract_config = '--user-patterns /tmp/tesseract.patterns'
# tesseract_config = None


def get_text_from_image(image):
    words = {}
    options = {}
    match_words = {}
    match_options = {}
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
        text_parts = [t for t in text.split() if re.search(r'\w', t)]
        options[key] = ' '.join(text_parts)
        # if len(text.strip()):
        #     print(crop, str(rotate)[:1], str(contrast)[:1],
        #           ' '.join(text_parts))
        for word in text_parts:
            words[word] = words.get(word, []) + [key]
        match = re_patterns.search(options[key])
        if match:
            match_options[key] = options[key]
            for word in text_parts:
                match_words[word] = match_words.get(word, []) + [key]
    if not(words):
        return ''
    if match_options:
        options, words = match_options, match_words
    while len(options) > 1 and len(words):
        _, word, wopts = sorted((-len(val), word, val) for word, val in words.items())[0]
        words.pop(word, None)
        for w in list(words):
            words[w] = [wopt for wopt in words[w] if wopt in wopts]
            if not len(words[w]):
                words.pop(w)
        options = {k: v for k, v in options.items() if k in wopts}
    return next(iter(options.values()))


def ocr_images(args):
    meta = {}
    if args.collection and os.path.exists(args.collection):
        meta = json.load(open(args.collection))
    max_workers = psutil.virtual_memory().total // (4 * 1024 ** 3)
    max_workers = min(max_workers, multiprocessing.cpu_count())
    max_workers = max(1, max_workers)
    if args.verbose >= 2:
        sys.stderr.write('Worker pool: %d\n' % max_workers)
        sys.stderr.flush()
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as pool:
        tasks = [(src, pool.submit(ocr_image, src)) for src in args.source]
        while len(tasks):
            try:
                result = tasks[0][-1].result(0.1)
            except concurrent.futures.TimeoutError:
                continue
            src, task = tasks.pop(0)
            if args.verbose:
                sys.stderr.write('%s\n' % src)
                sys.stderr.flush()
            if not result:
                continue
            for key in result:
                text = result[key]
                filename = os.path.basename(src)
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
    if args.verbose >= 3:
        sys.stderr.write('  run time: %5.3fs\n' % (time.time() - start_time))


def ocr_image(src):
    result = {}
    try:
        ts = large_image.open(src)
    except Exception:
        return
    proc_time = time.time()
    for key in ts.getAssociatedImagesList():
        try:
            image, _ = ts.getAssociatedImage(key)
        except Exception:
            continue
        try:
            image = PIL.Image.open(io.BytesIO(image))
            if False:
                text = pytesseract.image_to_string(image, config=tesseract_config).strip()
                text = ' '.join(text.split())
            else:
                text = get_text_from_image(image)
            if text:
                result[key] = text
        except Exception:
            continue
    large_image.cache_util.cachesClear()
    if args.verbose >= 3:
        sys.stderr.write('  process time: %5.3fs\n' % (time.time() - proc_time))
    return result


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
    args = parser.parse_args()
    ocr_images(args)
