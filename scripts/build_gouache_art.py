"""Deliver reviewed gouache PNGs without editing or replacing their pixels."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
STYLE_SHA = '26ab89260193f8bd34e29f2e796e8fe352341505d20bdb878e6da1e599821d07'


def build(selection_dir, root=ROOT, allow_incomplete=False):
    root, selection_dir = Path(root).resolve(), Path(selection_dir).resolve()
    approved = set(json.loads((root / 'dashboard_assets/circuit/catalogo_visual.json').read_text())['circuitos'])
    selections = {p.stem: json.loads(p.read_text()) for p in selection_dir.glob('*.json')}
    if not set(selections) <= approved or (not allow_incomplete and set(selections) != approved):
        raise ValueError('Every approved circuit requires its own reviewed illustration')
    sources, records = {}, {}
    for cid, spec in sorted(selections.items()):
        review = spec.get('visual_review')
        if (spec.get('circuit_id') != cid or spec.get('style_reference_sha256') != STYLE_SHA
                or not isinstance(review, dict) or review.get('status') != 'accepted_for_integration'):
            raise ValueError('Artwork identity, style or visual review is missing: ' + cid)
        source = selection_dir.parent / spec['original']
        if (source.is_symlink() or (selection_dir.parent / 'originais').is_symlink()
                or source.resolve().parent != (selection_dir.parent / 'originais').resolve()):
            raise ValueError('Original must be a regular file in the reviewed collection')
        raw = source.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if (digest != spec['sha256'] or raw[:8] != b'\x89PNG\r\n\x1a\n'
                or raw[12:16] != b'IHDR' or struct.unpack('>II', raw[16:24]) != (spec['width'], spec['height'])):
            raise ValueError('Original bytes or dimensions differ: ' + cid)
        path = 'static/pitwall-art/gouache/{}-{}.png'.format(cid, digest[:12])
        target = root / path
        if any((root / part).is_symlink() for part in ('static', 'static/pitwall-art', 'static/pitwall-art/gouache', path)):
            raise ValueError('Delivery paths must not be symlinks')
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('Existing immutable artwork differs: ' + cid)
        sources[cid] = (source, target)
        records[cid] = {key: spec[key] for key in
                       ('circuit_id', 'name', 'country', 'motif', 'reference_urls', 'alt', 'sha256', 'width', 'height')}
        records[cid]['path'] = path
    for source, target in sources.values():
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    catalogue = dict(schema=1, style='gouache-editorial', style_reference_sha256=STYLE_SHA,
                     complete=set(selections) == approved, circuits=records)
    target = root / 'frontend_assets/destination_illustrations.json'
    if target.is_symlink() or (root / 'frontend_assets').is_symlink():
        raise ValueError('Catalogue delivery path must not be a symlink')
    target.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + '\n')
    return catalogue


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection-dir', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--allow-incomplete', action='store_true', help='Local preview only; final checks require complete coverage')
    args = parser.parse_args()
    result = build(args.selection_dir, args.root, args.allow_incomplete)
    print(json.dumps({'circuits': len(result['circuits']), 'complete': result['complete'], 'style': result['style']}))
