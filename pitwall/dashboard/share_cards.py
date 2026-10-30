"""Standalone SVG exports: scoped historical facts, no external assets or scripts."""
from html import escape
from textwrap import wrap


def card_svg(title, scope, facts, source, english=False):
    title_lines = wrap(str(title), width=42)[:2]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img">',
             '<rect width="1200" height="630" fill="#e8f3fc"/>',
             '<path d="M48 100V530" stroke="#d3071d" stroke-width="6"/>',
             '<g fill="#102b50" font-family="Arial,sans-serif"><text x="80" y="65" font-size="24">Pitwall Lab</text>']
    for i, line in enumerate(title_lines):
        parts.append('<text x="80" y="{}" font-family="Georgia,serif" font-size="44">{}</text>'.format(150 + i * 55, escape(line)))
    parts.append('<text x="80" y="260" font-size="21">{}</text>'.format(escape(scope)))
    for i, fact in enumerate(facts[:4]):
        parts.append('<text x="80" y="{}" font-size="23">{}</text>'.format(325 + i * 46, escape(str(fact))))
    notice = "Historical results; not a prediction" if english else "Resultados históricos; não é uma previsão"
    parts.append('<text x="80" y="550" font-size="18">{}</text>'.format(escape(source)))
    parts.append('<text x="80" y="585" font-size="18">{}</text></g></svg>'.format(escape(notice)))
    return "".join(parts).encode("utf-8")
