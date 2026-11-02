"""Responsive delivery of documented photos; originals remain immutable."""
from functools import lru_cache
from html import escape
import json
from pitwall.paths import PROJECT_ROOT


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
