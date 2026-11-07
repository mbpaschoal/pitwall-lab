"""Identity-checked immutable gouache illustrations for circuit covers."""
import hashlib
import json
from pathlib import Path
import re
import struct

STYLE = 'gouache-editorial'
CATALOG = 'frontend_assets/destination_illustrations.json'


def illustration(root, circuit_id):
    """Return only this circuit's verified artwork, never a substitute."""
    if not isinstance(circuit_id, str) or not re.fullmatch(r'[a-z0-9_]+', circuit_id):
        return None
    root = Path(root).resolve()
    catalogue = root / CATALOG
    if catalogue.is_symlink() or (root / 'frontend_assets').is_symlink():
        return None
    try:
        data = json.loads(catalogue.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or type(data.get('schema')) is not int
                or data['schema'] != 1 or data.get('style') != STYLE):
            return None
        spec = data['circuits'][circuit_id]
        digest, relative = spec['sha256'], spec['path']
        if (spec.get('circuit_id') != circuit_id or not isinstance(digest, str)
                or not re.fullmatch(r'[a-f0-9]{64}', digest)
                or relative != 'static/pitwall-art/gouache/{}-{}.png'.format(circuit_id, digest[:12])):
            return None
        path = root / relative
        if any((root / part).is_symlink() for part in
               ('static', 'static/pitwall-art', 'static/pitwall-art/gouache', relative)):
            return None
        raw = path.read_bytes()
        if (raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR'
                or hashlib.sha256(raw).hexdigest() != digest):
            return None
        width, height = struct.unpack('>II', raw[16:24])
        if (type(spec.get('width')) is not int or type(spec.get('height')) is not int
                or (width, height) != (spec['width'], spec['height'])
                or width < 1536 or height < 1024 or width * 2 != height * 3):
            return None
        alt = spec['alt']
        if not isinstance(alt, list) or len(alt) != 2 or not all(isinstance(t, str) and t for t in alt):
            return None
        references = spec.get('reference_urls', [])
        if not isinstance(references, list) or not all(isinstance(url, str) for url in references):
            return None
        return dict(spec, src='app/' + relative)
    except (OSError, ValueError, KeyError, TypeError, struct.error):
        return None
