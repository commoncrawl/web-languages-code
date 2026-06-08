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
from collections import defaultdict

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
        '', md, flags=re.DOTALL | re.MULTILINE)
    # fix lists
    md = re.sub(r'^- ', '\n* ', md)
    # convert bare URLs into links
    md = re.sub(r' (https?://\S+)(?=\s|$)', r' <\1>', md)
    return md


def repair_empty_authority(u):
    """Repair a URL whose authority is empty (e.g. `https:///bla.bla.com`),
    where the host ended up in the path because of one slash too many.
    Promote the first non-empty path segment to be the host and rebuild
    the URL. Return a repaired URL string, or None if nothing can be
    recovered (e.g. `https:///` has no path segment to promote).

    `u` is the urllib.parse.ParseResult of the malformed URL.
    """
    if not u.startswith("http"):
        return None
    host, _, rest = u.path.lstrip('/').partition('/')
    if not host:
        return None
    return urlunparse((u.scheme, host, '/' + rest, u.params, u.query, u.fragment))


def normalize_url(url):
    """Normalize URL: encode IDN host, replace empty path by `/`,
    strip user and password from authority.

    Return the normalized URL string, or `None` when there is no crawlable
    host to normalize: relative URLs (e.g. `/path/page.html`, `about.html`),
    non-http(s) schemes (e.g. `mailto:`), and empty-authority inputs from
    which no host can be recovered."""

    # Fast path for already-clean http(s) URLs. `[^/@]+` forbids an `@`,
    # so URLs carrying `user:password@` credentials fall through to the slow
    # path below, where the authority is rebuilt from the host alone.
    if url.isascii() and re.match(r'^https?://[^/@]+/', url):
        return url
    u = urlparse(url)
    h = u.hostname
    if not h:
        # Empty authority. Only repair the one specific malformed shape
        # `http(s):///host...`, where an extra slash pushed the host into
        # the path. We match that literal prefix rather than just checking
        # the scheme: `http:foo/bar` and `mailto:me@x` also parse to an
        # empty authority, but promoting their first path segment to a host
        # (`http://foo/bar`, `mailto://me@x`) would fabricate a bogus URL.
        # Relative URLs (`/path`, `about.html`) have no host either. Drop
        # all of those.
        if not re.match(r'(?i)^https?:///', url):
            return None
        # Recover the host from the path, then re-normalize. The repaired
        # URL has a real host, so it can't re-enter this branch.
        repaired = repair_empty_authority(u)
        return normalize_url(repaired) if repaired else None
    # Only http(s) URLs are crawlable web links; drop any other scheme
    # (e.g. `ftp:`, or a scheme-less protocol-relative `//host/...`) even
    # when it carries a host.
    if not u.scheme.startswith("http"):
        return None
    # Rebuild the authority from the host alone, dropping any
    # `user:password@` credentials. IDN-encode non-ASCII hosts.
    n = h.encode('idna').decode('ascii') if not h.isascii() else h
    if u.port:
        # u.port is an int; cast before concatenating onto the host.
        n += ':' + str(u.port)
    p = u.path or '/'
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


total_accepted = 0
total_pattern_excluded = 0
total_unparseable = 0
live = defaultdict(int)

for path in web_languages_files:
    md = get_markdown_clean(path)
    html = markdown.markdown(md, stripTopLevelTags=False)
    soup = None
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception as e:
        logging.error('Error in converted HTML from <%s>: %s', path, e)
        continue
    links = []
    links_not_parseable = []
    for link in soup.find_all('a', href=True):
        link_str = link['href'] if 'href' in link else None
        normalized = normalize_url(link_str)
        if normalized:
            links.append(normalized)
        else:
            # No crawlable host (relative, mailto:, unrecoverable). Drop it.
            links_not_parseable.append(link['href'])

    # With exclusions disabled (`--exclude ''`), exclusion_pattern is None,
    # so nothing is excluded.
    if exclusion_pattern:
        links_exclusions = [exclusion_pattern.search(link) for link in links]
    else:
        links_exclusions = [None] * len(links)
    # Three disjoint buckets, all derived from the same total extracted count.
    n_pattern_excluded = len(list(filter(lambda e_: e_, links_exclusions)))
    n_unparseable = len(links_not_parseable)
    n_accepted = len(links) - n_pattern_excluded
    # Total links extracted from this file: parseable + unparseable. The
    # parseable ones split into accepted and pattern-excluded.
    n_total = len(links) + n_unparseable
    n_excluded = n_pattern_excluded + n_unparseable
    print('### {} links from {}{}'.format(
        n_accepted, path,
        ' (excluded: {} out of {})'.format(n_excluded, n_total)
        if n_excluded else ''))
    total_accepted += n_accepted
    total_pattern_excluded += n_pattern_excluded
    total_unparseable += n_unparseable
    for link, excluded in zip(links, links_exclusions):
        if excluded:
            print('##-', link)
        else:
            print(link)
            live[path] += 1


logging.info('Found %d links in %d markdown files.',
             total_accepted + total_pattern_excluded + total_unparseable,
             len(web_languages_files))
logging.info('Accepted %d links, %d excluded by pattern, %d unparseable.',
             total_accepted, total_pattern_excluded, total_unparseable)
logging.info('%d languages have non-excluded links',
             len(live))
