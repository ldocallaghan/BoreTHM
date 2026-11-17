"""Website links retain local navigation and point to versioned source files."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import docs_links


def test_source_data_and_archive_links_use_the_release():
    docs = ROOT / 'docs'
    for path, expected in [('../../src/borethm/site_files.py#load_site', 'blob/v1.5.0/src/borethm/site_files.py#load_site'),
                           ('../../results/', 'tree/v1.5.0/results'),
                           ('../../validation/forge16b/README.md', 'blob/v1.5.0/validation/forge16b/README.md')]:
        link = docs_links.rewrite_link(path, 'guides/new-site.md', docs, 'v1.5.0')
        assert link == 'https://github.com/ldocallaghan/BoreTHM/' + expected


def test_internal_and_external_links_are_unchanged():
    for link in ('../api.md#load_site', '#heading', 'https://example.com/file.md', '/absolute/path'):
        assert docs_links.rewrite_link(link, 'guides/new-site.md', ROOT / 'docs', 'v1.5.0') == link


def test_images_outside_the_docs_are_served_from_the_site():
    page = SimpleNamespace(file=SimpleNamespace(src_uri='science/models.md'))
    config = dict(docs_dir=str(ROOT / 'docs'), extra=dict(source_ref='v1.5.0'))
    markdown = ('![profiles](../../figures/model1_profiles.png)\n'
                '![transients](../../figures/forge16a_transients.png?raw=1)\n'
                '[profiles](../../figures/model1_profiles.png)\n'
                '```md\n![example](../../figures/model1_profiles.png)\n```\n')
    result = docs_links.on_page_markdown(markdown, page, config, [])
    assert '![profiles](../assets/repo/figures/model1_profiles.png)' in result
    assert '![transients](../assets/repo/figures/forge16a_transients.png)' in result
    assert '[profiles](https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/figures/model1_profiles.png)' in result
    assert '```md\n![example](../../figures/model1_profiles.png)\n```' in result
    assert docs_links.page_images(markdown, 'science/models.md', ROOT / 'docs') == [
        'figures/model1_profiles.png', 'figures/forge16a_transients.png']


def test_images_inside_the_docs_and_missing_images_keep_their_links():
    assert docs_links.image_file('../api.md', 'guides/new-site.md', ROOT / 'docs') is None
    assert docs_links.image_file('https://example.com/a.png', 'guides/new-site.md', ROOT / 'docs') is None
    assert docs_links.image_file('../../figures/missing.png', 'science/models.md', ROOT / 'docs') is None
    assert docs_links.image_link('figures/a.png', 'README.md') == 'assets/repo/figures/a.png'


def test_links_outside_the_repository_are_rejected():
    with pytest.raises(ValueError, match='outside the repository'):
        docs_links.image_file('../../../elsewhere.png', 'science/models.md', ROOT / 'docs')


def test_markdown_links_change_but_code_examples_do_not():
    page = SimpleNamespace(file=SimpleNamespace(src_uri='README.md'))
    config = dict(docs_dir=str(ROOT / 'docs'), extra=dict(source_ref='v1.5.0'))
    markdown = '[project](../README.md)\n[ref]: ../NOTICE\n```md\n[example](../README.md)\n```\n'
    result = docs_links.on_page_markdown(markdown, page, config, [])
    assert '[project](https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/README.md)' in result
    assert '[ref]: https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/NOTICE' in result
    assert '```md\n[example](../README.md)\n```' in result
