"""
Extract links from "web-languages" Markdown files
located at https://github.com/commoncrawl/web-languages/

After cloning the web-languages repository, navigate
into the web-languages directory and execute this script.
The extracted links are written to stdout, lines starting
with the # character are to be ignored.

Call with command-line flags -h or --help for additional options.
"""

import argparse
import glob
import logging
import sys
import markdown
import os
import re

from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup


LOGGING_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
LOG_LEVEL = 'INFO'
logging.basicConfig(level=LOG_LEVEL, format=LOGGING_FORMAT)


def get_markdown_clean(path):
    """Read Markdown from file and convert it into a form
    the Python Markdown parser is able to parse"""
    md = open(path, encoding='utf-8').read()
    # strip trailing instructions and supportive information
    md = re.sub(
        r'^(?:## Instructions|Informative links \(in English\)|Additional Information|Scripts|Thank you to these people who have helped create this document):.*',
        '', md, flags=re.DOTALL|re.MULTILINE)
    # fix lists
    md = re.sub(r'^- ', '\n* ', md)
    # convert bare URLs into links
    md = re.sub(r' (https?://\S+)(?=\s|$)', r' <\1>', md)
    return md

def normalize_url(url):
    """Normalize URL: encode IDN host, replace empty path by `/`,
    strip user and password from authority."""
    if url.isascii() and re.match(r'^https?://[^/]+/', url):
        return url
    u = urlparse(url)
    h = u.hostname
    n = u.netloc
    if not h.isascii():
        n = h.encode('idna').decode('ascii')
        if u.port:
            n += ':' + u.port
    p = u.path
    if u.path == '':
        p = '/'
    return urlunparse((u.scheme, n, p, u.params, u.query, ''))


web_languages_folders = [
    'living',
    'constructed',
    'extinct',
    'historical'
]

web_languages_files = []

for folder in web_languages_folders:
    for path in glob.iglob(os.path.join(folder, '*.md')):
        if path.endswith('README.md'):
            # skip READMEs
            continue
        web_languages_files.append(path)


arg_parser = argparse.ArgumentParser(description=__doc__)
arg_parser.add_argument(
    '--exclude', type=str,
    default=r'^https?://[a-z0-9.-]+\.wikipedia\.org/',
    help='exclusion pattern (regular expression on URLs), '
    'the default excludes links from Wikipedia. '
    'Excluded links are commented out and marked by `##-`.')
args = arg_parser.parse_args(sys.argv[1:])

logging.info('Command-line arguments: %s', args)
exclusion_pattern = None
if args.exclude:
    logging.info('Excluding links / URLs matching %s', args.exclude)
    exclusion_pattern = re.compile(args.exclude)


logging.info('Extracting links from %d markdown files', len(web_languages_files))


total_links = 0
total_excluded = 0

for path in web_languages_files:
    md = get_markdown_clean(path)
    html = markdown.markdown(md, stripTopLevelTags=False)
    soup = None
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        logging.error('Error in converted HTML from <%s>: %s', path, e)
        continue
    links = list(map(normalize_url,
                     [link['href'] for link in soup.find_all('a', href=True)]))
    links_exclusions = list(map(lambda l: exclusion_pattern.search(l), links))
    n_excluded = len(list(filter(lambda e: e, links_exclusions)))
    print('### {} links from {}{}'.format(
        len(links) - n_excluded, path,
        ' (excluded: {} out of {})'.format(n_excluded, len(links))
        if n_excluded else ''))
    total_links += len(links) - n_excluded
    total_excluded += n_excluded
    for link, excluded in zip(links, links_exclusions):
        if excluded:
            print('##-', link)
        else:
            print(link)


logging.info('Found %d links in %d markdown files.',
             total_links + total_excluded, len(web_languages_files))
logging.info('Accepted %d links, %d excluded by pattern.',
             total_links, total_excluded)