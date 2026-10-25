"""Gera uma galeria local de conferência dos ativos visuais catalogados."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOGO = ROOT / 'dashboard_assets/circuit/catalogo_visual.json'
DESTINO = ROOT / 'docs/galeria_circuitos.html'


def main():
    dados = json.loads(CATALOGO.read_text(encoding='utf-8'))
    cards = []
    for circuito, ativos in sorted(dados['circuitos'].items()):
        foto, mapa = ativos['foto'], ativos['mapa']
        cards.append('''<article><h2>{nome}</h2><img src="../{foto}" alt="{alt}"><img class="mapa" src="../{mapa}" alt="Mapa do traçado de {nome}"><p>Foto: {autor_foto} · {licenca_foto}</p><p>Mapa: {autor_mapa} · {licenca_mapa}</p></article>'''.format(
            nome=html.escape(circuito.replace('_', ' ')), alt=html.escape(ativos.get('alt_foto') or circuito),
            foto=html.escape(foto['caminho']), mapa=html.escape(mapa['caminho']),
            autor_foto=foto['autor'], licenca_foto=foto['licenca'], autor_mapa=mapa['autor'], licenca_mapa=mapa['licenca']))
    pendentes = 26 - len(dados['circuitos'])
    situacao = ('Cobertura completa do inventário local.' if not pendentes
                else 'Pendentes explícitos: {}/26, após HTTP 429 da Wikimedia.'.format(pendentes))
    DESTINO.write_text('''<!doctype html><meta charset="utf-8"><title>Galeria de circuitos — Pitwall Lab</title>
<style>body{{font-family:Arial,sans-serif;margin:24px;color:#112f57;background:#eef4fa}}header{{max-width:1100px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:18px}}article{{background:#fff;border:1px solid #cdd9e6;padding:14px}}h1,h2{{font-family:Georgia,serif}}h2{{text-transform:capitalize;margin-top:0}}img{{width:100%;height:185px;object-fit:cover;background:#e6edf5}}.mapa{{object-fit:contain;margin-top:8px}}p{{font-size:12px;margin:6px 0}}</style>
<header><h1>Galeria de conferência — circuitos</h1><p>Ativos locais com hash e licença verificados: {cobertos}/26. {situacao}</p></header><main>{cards}</main>'''.format(cobertos=len(dados['circuitos']), situacao=situacao, cards=''.join(cards)), encoding='utf-8')
    print(DESTINO)


if __name__ == '__main__':
    main()
