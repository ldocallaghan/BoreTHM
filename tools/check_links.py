"""Check local Markdown links without requiring a particular release version.

The path and heading checks are extracted from verify_v135_docs.py. Historical
release records and archived reviews retain the paths used at their tags.
"""
from collections import Counter
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_RELEASES = frozenset(('v1.3.6.md',))


def reader_documents(root=ROOT):
    root = Path(root)
    documents = [root / name for name in ('README.md', 'CONTRIBUTING.md', 'SUPPORT.md')]
    documents.extend(sorted((root / 'benchmarks').rglob('*.md')))
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


def check_documents(documents):
    """Return missing local paths or heading anchors as readable messages."""
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
                continue
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
    print(f'Checked relative links in {len(documents)} Markdown files.')


if __name__ == '__main__':
    main()
