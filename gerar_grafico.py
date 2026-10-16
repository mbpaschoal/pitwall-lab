"""Gráfico estático, sem dependências externas ou novas consultas à API."""
import argparse
import csv
from html import escape
from pathlib import Path
import sys

from coletar_resultados import salvar_preservando

RAIZ = Path(__file__).resolve().parent
STATUS_PT = {
    'Finished': 'Terminou',
    'Retired': 'Abandonou',
    'Did not start': 'Não largou',
    'Disqualified': 'Desclassificado',
}


def gerar(saida):
    """Lê o CSV preservado e gera SVG e HTML autocontidos."""
    fonte = RAIZ / 'data/resultados_sao_paulo_2024.csv'
    with fonte.open(encoding='utf-8', newline='') as arquivo:
        linhas = list(csv.DictReader(arquivo))
    if not linhas:
        raise ValueError('O CSV está vazio.')
    linhas.sort(key=lambda linha: int(linha['posicao_final']))
    posicoes = [int(linha[chave]) for linha in linhas for chave in ('posicao_largada', 'posicao_final')]
    if min(posicoes) < 1 or max(posicoes) > 20:
        raise ValueError('Este gráfico espera posições entre 1 e 20; confira o CSV.')
    altura = 225 + len(linhas) * 29 + 100
    # Mesmo eixo para os dois marcadores: posição 1 à esquerda, 20 à direita.
    x_inicial, passo = 239, 28
    partes = [f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 {altura}" role="img" aria-labelledby="titulo descricao">
<title id="titulo">São Paulo 2024: posição de largada e resultado por piloto</title>
<desc id="descricao">Um piloto por linha, ordenado pelo resultado da API. Círculo azul vazado: grid. Círculo verde cheio: resultado com status Finished. Losango âmbar: posição numérica com status especial, sem linha de comparação. Menor número é melhor. Fonte: CSV local da Jolpica-F1.</desc>
<style>
text {{ font-family: sans-serif; fill: var(--foreground, #172b40); }}
.muted {{ fill: var(--muted-foreground, #526477); }}
.grade {{ stroke: var(--border, #d9e1e9); stroke-width: 1; }}
.grid {{ stroke: #3983e6; stroke-width: 2.4; fill: var(--card, #ffffff); }}
.chegada {{ fill: #0d9c86; }}
.conexao {{ stroke: #0d9c86; stroke-opacity: .55; stroke-width: 3; }}
.especial {{ fill: #d18b15; stroke: var(--foreground, #172b40); stroke-width: .6; }}
</style>
<text x="16" y="31" font-size="13" letter-spacing="2" class="muted">PITWALL LAB / ANÁLISE EXPLORATÓRIA</text>
<text x="16" y="67" font-size="27" font-weight="700">Da largada ao resultado — São Paulo 2024</text>
<text x="16" y="91" font-size="13" class="muted">Corrida principal · 3 de novembro de 2024 · ordem da posição final informada pela API</text>
<circle cx="23" cy="119" r="6" class="grid"/><text x="38" y="124" font-size="13">Grid informado</text>
<circle cx="214" cy="119" r="5" class="chegada"/><text x="228" y="124" font-size="13">Final: terminou</text>
<polygon points="421,112 428,119 421,126 414,119" class="especial"/><text x="437" y="124" font-size="13">Posição da API: status especial (não comparar como chegada normal)</text>
<text x="16" y="164" font-size="12" font-weight="700" class="muted">PILOTO</text>
<text x="239" y="150" font-size="12" class="muted">← melhor posição / menor número</text>
<text x="829" y="164" font-size="12" font-weight="700" class="muted">STATUS</text>
<text x="1005" y="164" font-size="12" font-weight="700" text-anchor="middle" class="muted">SALDO*</text>''']
    fim_linhas = 193 + (len(linhas) - 1) * 29
    for posicao in range(1, 21):
        x = x_inicial + (posicao - 1) * passo
        partes.append(f'<line x1="{x}" y1="182" x2="{x}" y2="{fim_linhas + 15}" class="grade"/><text x="{x}" y="170" text-anchor="middle" font-size="11" class="muted">{posicao}</text>')
    for indice, linha in enumerate(linhas):
        y = 201 + indice * 29
        grid, final = int(linha['posicao_largada']), int(linha['posicao_final'])
        x_grid = x_inicial + (grid - 1) * passo
        x_final = x_inicial + (final - 1) * passo
        piloto, status = escape(linha['piloto'], quote=True), escape(linha['status'], quote=True)
        terminou = linha['status'] == 'Finished'
        partes.append(f'<g data-piloto="{piloto}" data-grid="{grid}" data-final="{final}" data-status="{status}">')
        partes.append(f'<title>{piloto}: grid {grid}; posição API {final}; {status}</title>')
        partes.append(f'<text x="16" y="{y + 4}" font-size="14">{piloto}</text>')
        if terminou:
            partes.append(f'<line x1="{x_grid}" y1="{y}" x2="{x_final}" y2="{y}" class="conexao"/>')
        partes.append(f'<circle cx="{x_grid}" cy="{y}" r="6.4" class="grid"/>')
        if terminou:
            partes.append(f'<circle cx="{x_final}" cy="{y}" r="4.4" class="chegada"/>')
            saldo = grid - final
            saldo_texto = '{:+d}'.format(saldo) if saldo else '0'
        else:
            partes.append(f'<polygon points="{x_final},{y-6} {x_final+6},{y} {x_final},{y+6} {x_final-6},{y}" class="especial"/>')
            saldo_texto = '—'
        partes.append(f'<text x="829" y="{y + 4}" font-size="12">{escape(STATUS_PT.get(linha["status"], linha["status"]))}</text>')
        partes.append(f'<text x="1005" y="{y + 4}" text-anchor="middle" font-size="13" font-weight="700">{saldo_texto}</text>')
        partes.append('</g>')
    rodape = fim_linhas + 52
    partes.extend([
        f'<text x="16" y="{rodape}" font-size="12" class="muted">* Saldo = grid − posição final, calculado apenas para Finished. Positivo: avançou; negativo: recuou.</text>',
        f'<text x="16" y="{rodape + 22}" font-size="12" class="muted">Saldo não é contagem de ultrapassagens. Para quem não largou, o círculo azul mostra apenas o grid informado.</text>',
        f'<text x="16" y="{rodape + 44}" font-size="12" class="muted">Fonte: Jolpica-F1 · data/resultados_sao_paulo_2024.csv · dados CC BY-NC-SA 4.0</text>',
        '</svg>',
    ])
    svg = '\n'.join(partes)
    html = '''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pitwall Lab — largada e resultado</title>
<style>svg{display:block;width:100%;height:auto}main{width:1100px;max-width:100%}</style></head><body><main>''' + svg + '</main></body></html>\n'
    for extensao, conteudo in [('svg', svg), ('html', html)]:
        destino = saida / ('largada_vs_resultado_sp2024.' + extensao)
        salvar_preservando(destino, conteudo)
        print('Gráfico salvo/verificado: {}'.format(destino))
    print('Pilotos representados: {}'.format(len(linhas)))
    print('O CSV original não foi alterado; nenhuma consulta à API foi feita.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida-dir', type=Path, default=RAIZ / 'reports', help='Pasta de saída do SVG e HTML')
    argumentos = parser.parse_args()
    try:
        gerar(argumentos.saida_dir)
    except (OSError, ValueError, KeyError, TypeError) as erro:
        print('Falha ao gerar gráfico: {}'.format(erro), file=sys.stderr)
        sys.exit(1)
