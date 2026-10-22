"""Check local Markdown links without requiring a particular release version.

Checks relative links and absolute GitHub links to this repository's main
branch against the working tree. Archived reviews and historical release
records retain the paths used at their tags.
"""
from collections import Counter
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_RELEASES = frozenset(('v1.3.6.md', 'v1.4.0.md'))


def reader_documents(root=ROOT):
    root = Path(root)
    documents = [root / name for name in ('README.md', 'CONTRIBUTING.md', 'SUPPORT.md', 'CHANGELOG.md', 'scripts/README.md')]
    documents.extend(sorted((root / 'benchmarks').rglob('*.md')))
    documents.extend(sorted((root / 'src/borethm/data').rglob('*.md')))
    documents.extend(sorted((root / '.github').rglob('*.md')))
    for path in sorted((root / 'docs').rglob('*.md')):
        relative = path.relative_to(root / 'docs')
        if relative.parts[0] == 'archive':
            continue
        if relative.parts[0] == 'releases' and path.name in HISTORICAL_RELEASES:
            continue
        documents.append(path)
    return documents


def headings(path):
    """Return GitHub-style heading anchors, including repeated headings."""
    anchors, counts = set(), Counter()
    fenced = False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
            continue
        if fenced or not re.match(r'^#{1,6} ', line):
            continue
        heading = line.lstrip('# ').rstrip('# ').strip().lower()
        slug = re.sub(r'[^\w -]', '', heading).replace(' ', '-')
        suffix = f'-{counts[slug]}' if counts[slug] else ''
        anchors.add(slug + suffix)
        counts[slug] += 1
    return anchors


def check_documents(documents, root=ROOT):
    """Return missing local or default-branch repository paths and anchors."""
    root = Path(root).resolve()
    errors = []
    for doc in map(Path, documents):
        text = doc.read_text(encoding='utf-8')
        destinations = re.findall(r'\[[^\]]*\]\(([^)]+)\)', text)
        destinations += re.findall(r'^\[[^\]]+\]:\s*(\S+)', text, re.M)
        for destination in destinations:
            destination = destination.strip()
            link = (destination[1:].split('>', 1)[0] if destination.startswith('<')
                    else destination.split(' "', 1)[0])
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                parts = unquote(parsed.path).strip('/').split('/')
                repository = [part.casefold() for part in parts[:2]]
                if (parsed.scheme not in ('http', 'https') or parsed.hostname != 'github.com'
                        or repository != ['ldocallaghan', 'borethm']):
                    continue
                if len(parts) == 2:
                    target = root / 'README.md'
                elif len(parts) >= 4 and parts[2] in ('blob', 'tree') and parts[3] == 'main':
                    target = root.joinpath(*parts[4:])
                    if not target.resolve().is_relative_to(root):
                        errors.append(f'{doc}: {link}: path outside repository')
                        continue
                else:
                    continue
            else:
                target = doc.parent / unquote(parsed.path) if parsed.path else doc
            if not target.exists():
                errors.append(f'{doc}: {link}: missing path')
            elif parsed.fragment and target.suffix.lower() == '.md':
                if unquote(parsed.fragment) not in headings(target):
                    errors.append(f'{doc}: {link}: missing heading')
    return errors


def main():
    documents = reader_documents()
    errors = check_documents(documents)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Checked local and main-branch repository links in {len(documents)} Markdown files.')


if __name__ == '__main__':
    main()
