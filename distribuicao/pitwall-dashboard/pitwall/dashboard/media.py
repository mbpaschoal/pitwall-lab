"""Responsive delivery of documented photos; originals remain immutable."""
from functools import lru_cache
from html import escape
import base64
import hashlib
import json
from pathlib import Path
import re
from pitwall.paths import PROJECT_ROOT


def circuit_static_path(circuit_id, photo):
    """An immutable name binds one approved photograph to one circuit."""
    suffix = Path(photo.get('caminho', '')).suffix.lower()
    digest = photo.get('sha256', '')
    if (not re.fullmatch(r'[a-z0-9_]+', str(circuit_id))
            or not isinstance(digest, str)
            or not re.fullmatch(r'[a-f0-9]{64}', digest)
            or suffix not in ('.jpg', '.jpeg', '.png', '.webp')):
        return None
    return 'static/pitwall-circuits/{}-{}{}'.format(circuit_id, digest[:12], suffix)


@lru_cache(maxsize=128)
def _matches(path, digest, modified, size):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == digest


@lru_cache(maxsize=64)
def _inline_photo(path, mime, modified, size):
    return 'data:{};base64,{}'.format(mime, base64.b64encode(Path(path).read_bytes()).decode('ascii'))


def circuit_photo_source(root, circuit_id, photo):
    """Serve the exact documented bytes, with a verified inline fallback."""
    root = Path(root).resolve()
    source = root / photo.get('caminho', '')
    relative = circuit_static_path(circuit_id, photo)
    if (relative is None or source.is_symlink()
            or (root / 'dashboard_assets').is_symlink()
            or (root / 'dashboard_assets/circuit').is_symlink()
            or source.resolve().parent != (root / 'dashboard_assets/circuit').resolve()
            or not source.is_file()):
        return ''
    digest = photo['sha256']
    stat = source.stat()
    if not _matches(str(source), digest, stat.st_mtime_ns, stat.st_size):
        return ''
    static = root / relative
    if (static.is_file() and not static.is_symlink()
            and not (root / 'static').is_symlink()
            and not (root / 'static/pitwall-circuits').is_symlink()):
        stat = static.stat()
        if _matches(str(static), digest, stat.st_mtime_ns, stat.st_size):
            # Relative to the app frame, including the Cloud /~/+/ prefix.
            return 'app/' + relative
    stat = source.stat()
    mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}[source.suffix.lower()]
    return _inline_photo(str(source), mime, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=1)
def _catalogue():
    return json.loads((PROJECT_ROOT / 'static/pitwall-media/catalog.json').read_text(encoding='utf-8'))


def responsive_attributes(spec):
    """Use only explicit local variants, never paths supplied by a visitor."""
    if spec.get('path') != 'dashboard_assets/fan/photos/antonelli-cockpit-mercedes.jpg':
        return None
    item = _catalogue()['method']
    if item['source_sha256'] != spec.get('sha256'):
        raise ValueError('Responsive photo does not match its documented original')
    variants = item['variants']
    for variant in variants:
        if not (PROJECT_ROOT / variant['path']).is_file():
            raise ValueError('Responsive photo variant is missing: ' + variant['path'])
    urls = [('app/' + v['path'], v['width']) for v in variants]
    srcset = ', '.join('{} {}w'.format(url, width) for url, width in urls)
    return 'src="{}" srcset="{}" sizes="(max-width:600px) 135vw, (min-width:1300px) 1742px, 140vw"'.format(
        escape(urls[0][0], quote=True), escape(srcset, quote=True))
