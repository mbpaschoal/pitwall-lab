"""Copy approved circuit originals into immutable same-origin delivery paths."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pitwall.data.visual_catalog import carregar
from pitwall.dashboard.media import circuit_static_path


def build(root=ROOT):
    root = Path(root).resolve()
    if (root / 'static').is_symlink() or (root / 'static/pitwall-circuits').is_symlink():
        raise ValueError('Static delivery directories must be regular local directories')
    records = []
    for circuit_id, assets in sorted(carregar(root).items()):
        photo = assets['foto']
        relative = circuit_static_path(circuit_id, photo)
        if relative is None:
            raise ValueError('Unsupported circuit photograph: ' + circuit_id)
        source, target = root / photo['caminho'], root / relative
        if target.is_symlink():
            raise ValueError('Static photograph must be a regular file: ' + relative)
        if target.exists():
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != photo['sha256']:
                    raise ValueError('Existing static photograph differs: ' + relative)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        records.append(dict(circuit_id=circuit_id, source=photo['caminho'], path=relative,
                            sha256=photo['sha256'], bytes=target.stat().st_size))
    return records


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
