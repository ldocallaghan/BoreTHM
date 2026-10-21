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
