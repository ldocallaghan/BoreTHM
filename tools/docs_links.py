"""Keep repository-relative source links usable on the documentation website."""
import importlib.util
import os
from pathlib import Path
import re
import tomllib
from urllib.parse import quote, unquote, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/ldocallaghan/BoreTHM'
INLINE_LINK = re.compile(r'(!?\[[^\]\n]*\]\()(<[^>]+>|[^\s)]+)')
REFERENCE_LINK = re.compile(r'^(\s{0,3}\[[^\]]+\]:\s*)(<[^>]+>|\S+)')


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


def rewrite_link(link, source, docs_dir, ref):
    """Rewrite a relative file outside the published docs to its GitHub URL."""
    parsed = urlsplit(link)
    if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith('/'):
        return link
    docs_dir = Path(docs_dir).resolve()
    target = (docs_dir / source).parent.joinpath(unquote(parsed.path)).resolve()
    if target.is_relative_to(docs_dir) and not target.is_relative_to(docs_dir / 'archive'):
        return link
    root = docs_dir.parent
    if not target.is_relative_to(root):
        raise ValueError(f'{source}: link outside the repository: {link}')
    # Historical records retain paths from their own releases.
    if not target.exists() and Path(source).parent == Path('releases'):
        ref = Path(source).stem
    kind = 'tree' if target.is_dir() else 'blob'
    path = '/'.join((kind, quote(ref, safe=''), quote(target.relative_to(root).as_posix(), safe='/')))
    return urlunsplit(('https', 'github.com', '/ldocallaghan/BoreTHM/' + path, parsed.query, parsed.fragment))


def on_page_markdown(markdown, page, config, files):
    source = page.file.src_uri
    ref = config['extra']['source_ref']
    def replace(match):
        original = match[2]
        angled = original.startswith('<')
        link = original[1:-1] if angled else original
        rewritten = rewrite_link(link, source, config['docs_dir'], ref)
        return match[1] + ('<' + rewritten + '>' if angled else rewritten)
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
            lines.append(REFERENCE_LINK.sub(replace, INLINE_LINK.sub(replace, line)))
        else:
            lines.append(line)
    return ''.join(lines)
