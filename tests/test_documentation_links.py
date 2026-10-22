"""Reader documentation links remain usable after moves and new releases."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_links import check_documents, reader_documents


def test_reader_documentation_links_resolve():
    errors = check_documents(reader_documents())
    assert not errors, '\n'.join(errors)


def test_checker_reports_missing_paths_and_headings(tmp_path):
    page = tmp_path / 'page.md'
    page.write_text('# A heading\n\n# A heading\n\n'
                    '[valid](#a-heading-1)\n[missing](absent.md)\n'
                    '[heading](#absent)\n[external](https://example.com)\n', encoding='utf-8')
    errors = check_documents([page])
    assert len(errors) == 2
    assert 'absent.md: missing path' in errors[0]
    assert '#absent: missing heading' in errors[1]


def test_absolute_main_branch_links_are_checked_locally(tmp_path):
    guide = tmp_path / 'guide.md'
    guide.write_text('# A guide\n', encoding='utf-8')
    (tmp_path / 'examples').mkdir()
    page = tmp_path / 'README.md'
    page.write_text('# Project\n\n'
                    '[guide](https://github.com/ldocallaghan/BoreTHM/blob/main/guide.md#a-guide)\n'
                    '[directory](https://github.com/ldocallaghan/BoreTHM/tree/main/examples)\n'
                    '[root](https://github.com/ldocallaghan/BoreTHM#project)\n'
                    '[missing](https://github.com/ldocallaghan/BoreTHM/blob/main/absent.md)\n'
                    '[anchor](https://github.com/ldocallaghan/BoreTHM/blob/main/guide.md#absent)\n',
                    encoding='utf-8')
    errors = check_documents([page], root=tmp_path)
    assert len(errors) == 2
    assert 'absent.md: missing path' in errors[0]
    assert '#absent: missing heading' in errors[1]


def test_external_and_historical_urls_are_not_current_checkout_paths(tmp_path):
    page = tmp_path / 'page.md'
    page.write_text('[other](https://github.com/other/project/blob/main/absent.md)\n'
                    '[historical](https://github.com/ldocallaghan/BoreTHM/blob/v1.3.4/absent.md)\n'
                    '[issues](https://github.com/ldocallaghan/BoreTHM/issues)\n', encoding='utf-8')
    assert check_documents([page], root=tmp_path) == []


def test_reader_documents_include_data_scripts_and_changelog():
    documents = set(reader_documents())
    assert ROOT / 'CHANGELOG.md' in documents
    assert ROOT / 'scripts/README.md' in documents
    assert set((ROOT / 'src/borethm/data').rglob('*.md')) <= documents
    assert not any(path.is_relative_to(ROOT / 'docs/archive') for path in documents)
