"""Website links retain local navigation and point to versioned source files."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import docs_links


def test_source_data_and_archive_links_use_the_release():
    docs = ROOT / 'docs'
    for path, expected in [('../../src/borethm/site_files.py#load_site', 'blob/v1.5.0/src/borethm/site_files.py#load_site'),
                           ('../../results/', 'tree/v1.5.0/results'),
                           ('../archive/README.md', 'blob/v1.5.0/docs/archive/README.md')]:
        link = docs_links.rewrite_link(path, 'guides/new-site.md', docs, 'v1.5.0')
        assert link == 'https://github.com/ldocallaghan/BoreTHM/' + expected


def test_internal_and_external_links_are_unchanged():
    for link in ('../api.md#load_site', '#heading', 'https://example.com/file.md', '/absolute/path'):
        assert docs_links.rewrite_link(link, 'guides/new-site.md', ROOT / 'docs', 'v1.5.0') == link


def test_markdown_links_change_but_code_examples_do_not():
    page = SimpleNamespace(file=SimpleNamespace(src_uri='README.md'))
    config = dict(docs_dir=str(ROOT / 'docs'), extra=dict(source_ref='v1.5.0'))
    markdown = '[project](../README.md)\n[ref]: ../NOTICE\n```md\n[example](../README.md)\n```\n'
    result = docs_links.on_page_markdown(markdown, page, config, [])
    assert '[project](https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/README.md)' in result
    assert '[ref]: https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/NOTICE' in result
    assert '```md\n[example](../README.md)\n```' in result
