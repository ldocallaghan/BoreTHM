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


def test_links_to_maintenance_pages_go_to_github():
    for path, source, expected in [('maintenance/README.md', 'README.md', 'blob/v1.9.0/docs/maintenance/README.md'),
                                   ('../maintenance/release-checklist.md#v190', 'releases/v1.9.0.md',
                                    'blob/v1.9.0/docs/maintenance/release-checklist.md#v190')]:
        assert docs_links.rewrite_link(path, source, ROOT / 'docs', 'v1.9.0') == 'https://github.com/ldocallaghan/BoreTHM/' + expected


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


def test_an_image_and_its_caption_become_a_figure():
    html = ('<p><img alt="Profiles" src="../assets/repo/figures/a.png" /></p>\n'
            '<p><em>Fig. 1. Profiles from the <a href="../models/">model</a>, <em>illustrative</em>.</em></p>')
    nested = docs_links.on_page_content(html, None, None, None)
    assert nested == ('<figure><a href="../assets/repo/figures/a.png"><img alt="Profiles" src="../assets/repo/figures/a.png" /></a>'
                      '<figcaption><em>Fig. 1. Profiles from the <a href="../models/">model</a>, <em>illustrative</em>.</em></figcaption></figure>')
    plain = docs_links.on_page_content('<p><img alt="A" src="a.png" /></p>\n<p><em>Fig. 2. A <a href="b/">link</a>.</em></p>', None, None, None)
    assert plain == '<figure><a href="a.png"><img alt="A" src="a.png" /></a><figcaption>Fig. 2. A <a href="b/">link</a>.</figcaption></figure>'
    roman = docs_links.on_page_content('<p><img alt="A" src="a.png" /></p><p>Fig. 3. Upright.</p>', None, None, None)
    assert roman.endswith('<figcaption>Fig. 3. Upright.</figcaption></figure>')


def test_an_image_without_a_caption_becomes_a_figure_and_the_next_paragraph_stays():
    html = '<p><img alt="A" src="a.png" /></p>\n<p>The next paragraph.</p>\n<p><img alt="B" src="b.png" /></p>'
    assert docs_links.on_page_content(html, None, None, None) == (
        '<figure><a href="a.png"><img alt="A" src="a.png" /></a></figure>\n<p>The next paragraph.</p>\n'
        '<figure><a href="b.png"><img alt="B" src="b.png" /></a></figure>')


def test_fig_paragraphs_away_from_images_and_code_examples_are_left_alone():
    html = ('<p>Fig. 4 shows the result.</p>\n<p><em>Fig. 5. A caption with no image.</em></p>\n'
            '<pre><code>![A](a.png)\n&lt;p&gt;&lt;img src="a.png" /&gt;&lt;/p&gt;\n*Fig. 6. Text.*\n</code></pre>')
    assert docs_links.on_page_content(html, None, None, None) == html


def test_an_emphasised_paragraph_after_an_image_becomes_its_caption():
    html = ('<p><img alt="A" src="a.png" /></p>\n'
            '<p><em>Crop from the <a href="log.pdf">mud log</a>, page 2.</em></p>')
    assert docs_links.on_page_content(html, None, None, None) == (
        '<figure><a href="a.png"><img alt="A" src="a.png" /></a>'
        '<figcaption>Crop from the <a href="log.pdf">mud log</a>, page 2.</figcaption></figure>')
    partly = '<p><img alt="A" src="a.png" /></p>\n<p><em>Partly</em> emphasised text.</p>'
    assert docs_links.on_page_content(partly, None, None, None).endswith('</figure>\n<p><em>Partly</em> emphasised text.</p>')


def test_an_emphasised_paragraph_after_text_is_left_alone():
    html = '<p>Ordinary text.</p>\n<p><em>An emphasised remark.</em></p>'
    assert docs_links.on_page_content(html, None, None, None) == html


def test_markdown_links_change_but_code_examples_do_not():
    page = SimpleNamespace(file=SimpleNamespace(src_uri='README.md'))
    config = dict(docs_dir=str(ROOT / 'docs'), extra=dict(source_ref='v1.5.0'))
    markdown = '[project](../README.md)\n[ref]: ../NOTICE\n```md\n[example](../README.md)\n```\n'
    result = docs_links.on_page_markdown(markdown, page, config, [])
    assert '[project](https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/README.md)' in result
    assert '[ref]: https://github.com/ldocallaghan/BoreTHM/blob/v1.5.0/NOTICE' in result
    assert '```md\n[example](../README.md)\n```' in result
