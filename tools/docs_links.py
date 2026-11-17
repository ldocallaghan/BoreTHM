"""Keep repository-relative source links usable on the documentation website.

Images outside the published docs are copied into the site under
``assets/repo/`` and shown from there. Other links to files outside the
published docs point to their GitHub page at the release tag.
"""
import importlib.util
import os
from pathlib import Path
import posixpath
import re
import tomllib
from urllib.parse import quote, unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/ldocallaghan/BoreTHM'
INLINE_LINK = re.compile(r'(!?\[[^\]\n]*\]\()(<[^>]+>|[^\s)]+)')
REFERENCE_LINK = re.compile(r'^(\s{0,3}\[[^\]]+\]:\s*)(<[^>]+>|\S+)')
IMAGE_ASSETS = 'assets/repo'


def on_config(config):
    metadata = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    config['extra']['source_ref'] = os.environ.get('BORETHM_DOCS_REF', 'v' + metadata['project']['version'])
    return config


def on_pre_build(config):
    spec = importlib.util.spec_from_file_location('borethm_document_links', ROOT / 'tools/check_links.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    errors = checker.check_documents(checker.reader_documents())
    if errors:
        raise ValueError('Documentation links failed:\n' + '\n'.join(errors))


def outside_docs(link, source, docs_dir):
    """Return the target of a relative link to a path outside the published docs, or None."""
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith('/'):
        return None
    docs_dir = Path(docs_dir).resolve()
    target = (docs_dir / source).parent.joinpath(unquote(parsed.path)).resolve()
    if target.is_relative_to(docs_dir) and not target.is_relative_to(docs_dir / 'archive'):
        return None
    if not target.is_relative_to(docs_dir.parent):
        raise ValueError(f'{source}: link outside the repository: {link}')
    return target


def rewrite_link(link, source, docs_dir, ref):
    """Rewrite a relative file outside the published docs to its GitHub URL."""
    target = outside_docs(link, source, docs_dir)
    if target is None:
        return link
    parsed = urlsplit(link)
    root = Path(docs_dir).resolve().parent
    # Historical records retain paths from their own releases.
    if not target.exists() and Path(source).parent == Path('releases'):
        ref = Path(source).stem
    kind = 'tree' if target.is_dir() else 'blob'
    path = '/'.join((kind, quote(ref, safe=''), quote(target.relative_to(root).as_posix(), safe='/')))
    return urlunsplit(('https', 'github.com', '/ldocallaghan/BoreTHM/' + path, parsed.query, parsed.fragment))


def image_file(link, source, docs_dir):
    """Return the repository path of an image file outside the published docs, or None.

    A query string such as ``?raw=1`` is ignored."""
    target = outside_docs(link, source, docs_dir)
    if target is None or not target.is_file():
        return None
    return target.relative_to(Path(docs_dir).resolve().parent).as_posix()


def image_link(path, source):
    """Return the link from the page ``source`` to the site's copy of a repository image."""
    return posixpath.relpath(f'{IMAGE_ASSETS}/{path}', posixpath.dirname(source) or '.')


def outside_fences(markdown, change):
    """Apply ``change`` to each line of Markdown outside fenced code blocks."""
    lines = []
    fence = None
    for line in markdown.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append(line)
        elif fence is None:
            lines.append(change(line))
        else:
            lines.append(line)
    return ''.join(lines)


def page_images(markdown, source, docs_dir):
    """Return the repository paths of the images outside the published docs that a page shows."""
    found = []
    def collect(line):
        for match in INLINE_LINK.finditer(line):
            if match[1].startswith('!'):
                link = match[2][1:-1] if match[2].startswith('<') else match[2]
                path = image_file(link, source, docs_dir)
                if path is not None:
                    found.append(path)
        return line
    outside_fences(markdown, collect)
    return found


def on_files(files, config):
    from mkdocs.structure.files import File
    paths = set()
    for page in files.documentation_pages():
        markdown = Path(page.abs_src_path).read_text(encoding='utf-8-sig')
        paths.update(page_images(markdown, page.src_uri, config['docs_dir']))
    root = Path(config['docs_dir']).resolve().parent
    for path in sorted(paths):
        files.append(File.generated(config, f'{IMAGE_ASSETS}/{path}', abs_src_path=str(root / path)))
    return files


IMAGE_PARAGRAPH = re.compile(r'<p>\s*(<img\b[^>]*>)\s*</p>(?:(\s*)<p>(.*?)</p>)?', re.S)
WHOLE_EMPHASIS = re.compile(r'<em>((?:(?!</?em>).)*)</em>', re.S)


def figure(image, caption=None):
    """Return a figure that links to its full-size image, with the caption if there is one."""
    source = re.search(r'\ssrc="([^"]*)"', image)
    html = f'<figure><a href="{source[1]}">{image}</a>' if source else f'<figure>{image}'
    if caption is not None:
        whole = WHOLE_EMPHASIS.fullmatch(caption.strip())
        html += f'<figcaption>{whole[1] if whole else caption.strip()}</figcaption>'
    return html + '</figure>'


def on_page_content(html, page, config, files):
    """Turn each image paragraph, and a following paragraph that starts with "Fig.", into a figure."""
    def replace(match):
        image, gap, following = match[1], match[2], match[3]
        if following is not None and re.sub(r'<[^>]+>', '', following).lstrip().startswith('Fig.'):
            return figure(image, following)
        rest = '' if following is None else IMAGE_PARAGRAPH.sub(replace, f'{gap}<p>{following}</p>')
        return figure(image) + rest
    return IMAGE_PARAGRAPH.sub(replace, html)


def on_page_markdown(markdown, page, config, files):
    source = page.file.src_uri
    ref = config['extra']['source_ref']
    def replace(match):
        original = match[2]
        angled = original.startswith('<')
        link = original[1:-1] if angled else original
        image = image_file(link, source, config['docs_dir']) if match[1].startswith('!') else None
        if image is not None:
            rewritten = image_link(image, source)
        else:
            rewritten = rewrite_link(link, source, config['docs_dir'], ref)
        return match[1] + ('<' + rewritten + '>' if angled else rewritten)
    return outside_fences(markdown, lambda line: REFERENCE_LINK.sub(replace, INLINE_LINK.sub(replace, line)))
