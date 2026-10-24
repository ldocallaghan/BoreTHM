"""Compare exported JSON values with exact types and floating-point bits.

Object member order and JSON formatting are ignored. Float comparison
preserves signed zero. Non-finite JSON tokens are parsed by Python's JSON
decoder; NaNs compare by their decoded binary representation. Original NaN
payloads cannot be represented by a JSON token.
"""
import argparse
import json
from pathlib import Path
import struct

EXCLUSIONS = {
    '/versions': 'code/environment provenance',
    '/source_sha256': 'trial source/environment fingerprint',
    '/elapsed_seconds': 'trial elapsed time',
    '/evidence': 'trial output-file path',
}


def compare(before, after, excluded=('/versions',)):
    """Return every differing leaf and explicitly record metadata exclusions."""
    unknown = set(excluded)-EXCLUSIONS.keys()
    if unknown:
        raise ValueError('unsupported exclusion: '+', '.join(sorted(unknown)))
    excluded = set(excluded)
    differences, skipped = [], []

    def walk(a, b, path):
        if path in excluded:
            skipped.append(dict(path=path, reason=EXCLUSIONS[path]))
            return
        if type(a) is not type(b):
            differences.append(dict(path=path, kind='type', before=type(a).__name__, after=type(b).__name__))
        elif isinstance(a, dict):
            for key in sorted(a.keys() | b.keys()):
                child=path+'/'+key.replace('~','~0').replace('/','~1')
                if key not in a or key not in b:
                    if child in excluded:
                        skipped.append(dict(path=child,reason=EXCLUSIONS[child]))
                    else:
                        differences.append(dict(path=child,kind='missing',before=key in a,after=key in b))
                else:
                    walk(a[key],b[key],child)
        elif isinstance(a, list):
            if len(a)!=len(b):
                differences.append(dict(path=path,kind='length',before=len(a),after=len(b)))
            for i,(x,y) in enumerate(zip(a,b)):
                walk(x,y,path+'/'+str(i))
        elif isinstance(a,float):
            x,y=struct.pack('>d',a),struct.pack('>d',b)
            if x!=y:
                differences.append(dict(path=path,kind='float_bits',before=a,after=b,
                    before_bits=x.hex(),after_bits=y.hex()))
        elif a!=b:
            differences.append(dict(path=path,kind='value',before=a,after=b))
    walk(before,after,'')
    return dict(equal=not differences,exclusions_requested=sorted(excluded),
                excluded_fields=skipped,differences=differences)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before',type=Path)
    parser.add_argument('after',type=Path)
    parser.add_argument('--exclude',action='append',choices=EXCLUSIONS,default=None,
        help='metadata path to exclude; default: /versions')
    parser.add_argument('--include-versions',action='store_true',help='include version metadata in equality')
    parser.add_argument('--output',type=Path,help='write the comparison JSON to this path')
    args=parser.parse_args()
    excluded=args.exclude if args.exclude is not None else ([] if args.include_versions else ['/versions'])
    result=compare(json.loads(args.before.read_text(encoding='utf-8')),
                   json.loads(args.after.read_text(encoding='utf-8')),excluded)
    text=json.dumps(result,indent=2)+'\n'
    if args.output:
        args.output.write_text(text,encoding='utf-8')
    else:
        print(text,end='')
    return 0 if result['equal'] else 1


if __name__=='__main__':
    raise SystemExit(main())
