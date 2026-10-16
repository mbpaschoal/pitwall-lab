"""Análise exploratória descritiva de 2024 e referência retrospectiva top 3."""
from collections import Counter, defaultdict
import csv
import hashlib
from html import escape
import io
import json
from pathlib import Path
import sys

from coletar_temporada import PASTA, COLUNAS, coletar_paginas, montar_base
from coletar_resultados import salvar_preservando

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / 'reports/temporada_2024'


def resumir_analise(linhas):
    """Frequências descritivas e avaliação com denominadores explícitos."""
    grupos = defaultdict(list)
    for linha in linhas:
        grupos[(linha['temporada'], linha['rodada'])].append(linha)
    avaliacoes = [avaliar_corrida(grupos[chave]) for chave in sorted(grupos, key=lambda x: (int(x[0]), int(x[1])))]
    validas = [a for a in avaliacoes if a['avaliavel']]
    distribuicao = {str(i): sum(a['acertos'] == i for a in validas) for i in range(4)}
    frequencias = []
    grades = sorted({int(r['posicao_largada']) for r in linhas if int(r['posicao_largada']) > 0}) + [0]
    for grid in grades:
        grupo = [r for r in linhas if int(r['posicao_largada']) == grid]
        podios = sum(1 <= int(r['posicao_final']) <= 3 for r in grupo)
        frequencias.append({'grid': grid, 'registros': len(grupo), 'podios': podios,
                            'proporcao': podios / len(grupo) if grupo else None})
    total_podios = sum(1 <= int(r['posicao_final']) <= 3 for r in linhas)
    top3 = sum(1 <= int(r['posicao_final']) <= 3 and int(r['posicao_largada']) in (1, 2, 3) for r in linhas)
    extremos = [a['acertos'] for a in validas]
    return {'corridas': len(avaliacoes), 'corridas_avaliaveis': len(validas),
            'corridas_nao_avaliaveis': len(avaliacoes) - len(validas),
            'total_podios': total_podios, 'podios_top3_grid': top3,
            'proporcao_podios_top3_grid': top3 / total_podios if total_podios else None,
            'media_acertos': sum(extremos) / len(validas) if validas else None,
            'distribuicao_acertos': distribuicao,
            'proporcao_tres_corretos': distribuicao['3'] / len(validas) if validas else None,
            'frequencia_grid': frequencias, 'avaliacao_por_corrida': avaliacoes,
            'maior_correspondencia': [a['rodada'] for a in validas if a['acertos'] == max(extremos)] if extremos else [],
            'menor_correspondencia': [a['rodada'] for a in validas if a['acertos'] == min(extremos)] if extremos else []}


def avaliar_corrida(linhas):
    """Escolhe antes de olhar os resultados: somente grid 1, 2 e 3, sem filtro de status."""
    if not linhas:
        raise ValueError('Corrida sem registros')
    contagens = Counter(int(r['posicao_largada']) for r in linhas)
    problemas = ['grid {}: {} registros (esperado 1)'.format(g, contagens[g])
                 for g in (1, 2, 3) if contagens[g] != 1]
    escolhidos = sorted([r for r in linhas if int(r['posicao_largada']) in (1, 2, 3)],
                        key=lambda r: int(r['posicao_largada']))
    podio = sorted([r for r in linhas if 1 <= int(r['posicao_final']) <= 3],
                   key=lambda r: int(r['posicao_final']))
    if len(podio) != 3 or {int(r['posicao_final']) for r in podio} != {1, 2, 3}:
        raise ValueError('Pódio não contém exatamente as posições 1, 2 e 3')
    coincidencias = len({r['piloto_id'] for r in escolhidos} & {r['piloto_id'] for r in podio})
    return {'temporada': linhas[0]['temporada'], 'rodada': linhas[0]['rodada'],
            'corrida': linhas[0]['corrida'], 'circuito_id': linhas[0]['circuito_id'],
            'avaliavel': not problemas, 'problemas_grid': problemas,
            'escolhidos': escolhidos, 'podio_real': podio,
            'acertos': coincidencias if not problemas else None}


def carregar_base(pasta=PASTA):
    """Não acessa a rede: reconstrói a base do cache e confere CSV/comprovante."""
    try:
        comprovante = json.loads((pasta / 'verificacao.json').read_text(encoding='utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as erro:
        raise ValueError('Comprovante inválido; execute coletar_temporada.py após preservar os arquivos em backup') from erro
    if not isinstance(comprovante, dict) or comprovante.get('completa') is not True:
        raise ValueError('A base não possui comprovante de coleta completa')
    calendario, _ = coletar_paginas('calendario', pasta / 'raw', somente_cache=True)
    fragmentos, total = coletar_paginas('resultados', pasta / 'raw', somente_cache=True)
    esperadas, qualidade = montar_base(calendario, fragmentos, total)
    conteudo = (pasta / 'resultados_2024.csv').read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != comprovante.get('csv_sha256'):
        raise ValueError('CSV difere do comprovante; análise bloqueada para não usar base parcial ou alterada')
    with (pasta / 'resultados_2024.csv').open(encoding='utf-8', newline='') as arquivo:
        leitor = csv.DictReader(arquivo)
        if leitor.fieldnames != COLUNAS:
            raise ValueError('Cabeçalho do CSV inesperado')
        linhas = list(leitor)
    if linhas != esperadas or any(comprovante.get(k) != v for k, v in qualidade.items()):
        raise ValueError('CSV/comprovante não corresponde às respostas originais completas')
    hashes = comprovante.get('paginas_sha256')
    atuais = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((pasta / 'raw').glob('*.json'))}
    if hashes != atuais:
        raise ValueError('Páginas originais diferem do comprovante; preserve os arquivos e confira a coleta')
    return linhas, qualidade


def percentual(valor):
    return 'n/d' if valor is None else '{:.2f}%'.format(100 * valor).replace('.', ',')


def formatar_media(valor):
    return 'n/d' if valor is None else '{:.2f}'.format(valor)


def tabela_md(cabecalho, linhas):
    def celula(valor):
        return str(valor).replace('|', '\\|').replace('\n', ' ')
    partes = ['| ' + ' | '.join(cabecalho) + ' |', '| ' + ' | '.join(['---'] * len(cabecalho)) + ' |']
    partes += ['| ' + ' | '.join(celula(v) for v in linha) + ' |' for linha in linhas]
    return '\n'.join(partes)


def csv_texto(cabecalho, linhas):
    arquivo = io.StringIO(newline='')
    escritor = csv.DictWriter(arquivo, fieldnames=cabecalho, lineterminator='\n')
    escritor.writeheader()
    escritor.writerows(linhas)
    return arquivo.getvalue()


def grafico_barras(titulo, subtitulo, itens, maximo, marcas, nota):
    """SVG estático: rótulo, valor, anotação com contagem e cor em cada linha."""
    altura = 180 + len(itens) * 29
    inicio, largura = 305, 435
    partes = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{altura}" viewBox="0 0 1100 {altura}" role="img" aria-labelledby="titulo descricao">
<title id="titulo">{escape(titulo)}</title><desc id="descricao">{escape(subtitulo + '. ' + nota)}</desc>
<rect width="1100" height="{altura}" fill="#ffffff"/>
<style>text{{font-family:sans-serif;fill:#182d43}}.nota{{fill:#53667b}}</style>
<text x="18" y="27" font-size="12" letter-spacing="2" class="nota">PITWALL LAB / TEMPORADA 2024</text>
<text x="18" y="62" font-size="25" font-weight="700">{escape(titulo)}</text>
<text x="18" y="87" font-size="13" class="nota">{escape(subtitulo)}</text>''']
    for valor, rotulo in marcas:
        x = inicio + largura * valor / maximo
        partes.append(f'<line x1="{x}" x2="{x}" y1="125" y2="{125 + len(itens)*29}" stroke="#e0e7ed"/><text x="{x}" y="116" text-anchor="middle" font-size="11" class="nota">{escape(rotulo)}</text>')
    for numero, (rotulo, valor, anotacao, cor) in enumerate(itens):
        y = 141 + numero * 29
        w = largura * (valor or 0) / maximo
        partes.append(f'<g data-rotulo="{escape(rotulo, quote=True)}"><title>{escape(rotulo + ": " + anotacao)}</title><text x="18" y="{y+4}" font-size="13">{escape(rotulo)}</text>')
        partes.append(f'<rect x="{inicio}" y="{y-8}" width="{w}" height="16" rx="3" fill="{cor}"/>')
        if not valor:
            partes.append(f'<circle cx="{inicio}" cy="{y}" r="3" fill="{cor}"/>')
        partes.append(f'<text x="770" y="{y+4}" font-size="13">{escape(anotacao)}</text></g>')
    partes.append(f'<text x="18" y="{altura-24}" font-size="12" class="nota">{escape(nota)}</text></svg>')
    return '\n'.join(partes)


def gerar(saida=SAIDA, pasta_dados=PASTA):
    linhas, qualidade = carregar_base(pasta_dados)
    resumo = resumir_analise(linhas)
    frequencias, avaliacoes = resumo['frequencia_grid'], resumo['avaliacao_por_corrida']
    validas = resumo['corridas_avaliaveis']
    soma_acertos = sum(a['acertos'] for a in avaliacoes if a['avaliavel'])
    nomes = {a['rodada']: a['corrida'] for a in avaliacoes}
    maiores = ', '.join(nomes[r] for r in resumo['maior_correspondencia']) or 'nenhuma corrida avaliável'
    menores = ', '.join(nomes[r] for r in resumo['menor_correspondencia']) or 'nenhuma corrida avaliável'
    fontes = [
        ('Contrato, identificação e paginação Jolpica-F1', 'https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md'),
        ('Limites Jolpica-F1', 'https://github.com/jolpica/jolpica-f1/blob/main/docs/rate_limits.md'),
        ('Campos dos resultados Jolpica-F1', 'https://github.com/jolpica/jolpica-f1/blob/main/docs/endpoints/results.md'),
        ('Significado de grid zero na documentação original Ergast (arquivo)', 'https://web.archive.org/web/20240309224950/http://ergast.com/mrd/methods/results/'),
        ('Williams: atualização do GP da Austrália de 2024', 'https://www.williamsf1.com/articles/bc29d1d1-8148-41e5-8c6e-59d452682be6/australian-grand-prix-update'),
        ('F1: grid oficial do México de 2024 e largada de Ocon no pit lane', 'https://www.formula1.com/en/latest/article/official-grid-who-sits-where-in-mexico-city-as-ocon-takes-pit-lane-start.6vBvcKe77Nh9Qjwfyh6wuT'),
        ('Termos dos dados: CC BY-NC-SA 4.0', 'https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md'),
    ]
    textos = [
        '# Pitwall Lab — temporada 2024: grid e pódio',
        '## 1. O que foi construído e como reproduzir',
        'Coleta das **corridas principais**, sem sprints. Uma linha por piloto e corrida, com os identificadores estáveis da fonte. Somente biblioteca padrão do Python; nenhuma dependência nova, modelo ou dashboard.',
        'Dentro da pasta do projeto, execute:\n\n```bash\n./.venv/bin/python coletar_temporada.py\n./.venv/bin/python analisar_temporada.py\n./.venv/bin/python -m unittest discover -s tests -v\n```',
        'O calendário vem de `/2024/` e os resultados de `/2024/results/`, com `limit=100` e `offset` avançando pela quantidade recebida. O calendário válido da etapa 1 foi reaproveitado. Os JSON originais ficam em `data/temporada_2024/raw/`; CSV e comprovante de completude ficam em `data/temporada_2024/`. As respostas são um retrato versionado, não uma atualização automática da API.',
        'Cada página é validada antes de ser gravada; total, limite e offset precisam ser coerentes. Uma corrida pode atravessar páginas. O CSV final só é produzido após a conferência de todas as páginas, corridas, chaves e pódios. A análise não acessa a rede: reconstrói os dados do cache e confere CSV, comprovante e hashes. Conteúdo existente diferente não é sobrescrito; um erro não transforma caches parciais em base completa.',
        'Aplicativo `PitwallLab/0.2.0`, com versão do Python no User-Agent. Requisições sequenciais espaçadas por pelo menos 8 segundos. Limites documentados consultados: 4/s e 500/h, compartilhados pelo IP e sujeitos a alterações. HTTP 429 encerra a coleta e informa Retry-After; não há repetição automática. Não execute coletores simultaneamente.',
        '## 2. Verificação da base',
        tabela_md(['Verificação', 'Resultado'], [
            ['Corridas esperadas pelo calendário', qualidade['corridas_esperadas']],
            ['Corridas coletadas', qualidade['corridas_coletadas']], ['Registros', qualidade['registros']],
            ['Duplicações temporada/rodada/piloto', qualidade['duplicacoes_temporada_rodada_piloto']],
            ['Total de campos ausentes', sum(qualidade['campos_ausentes'].values())],
            ['Corridas avaliáveis para a regra', '{}/{}'.format(validas, resumo['corridas'])],
        ]),
        '### Registros e pódios por corrida',
        tabela_md(['Rodada', 'Corrida', 'Registros', 'Pilotos no pódio'], [[r['rodada'], r['corrida'], r['registros'], r['podios']] for r in qualidade['registros_por_corrida']]),
        '**Diferença investigada:** a Austrália tem 19 registros, não 20. O comunicado da Williams explica que, após o acidente de Albon e sem um terceiro chassi, ele usou o carro de Sargeant; Sargeant foi retirado do restante do fim de semana. O resultado da API tem Albon e não tem Sargeant. Não foi inventada uma linha para preencher a contagem. As outras corridas têm 20 registros nesta extração, mas o coletor não impõe 20 como regra: confere o total da API e o calendário.',
        'O contexto da Williams é informação externa documentada, não uma causa deduzida do CSV. Os links estão ao final.',
        '### Campos ausentes',
        tabela_md(['Campo', 'Ausentes'], qualidade['campos_ausentes'].items()),
        '### Status: nenhum registro foi excluído',
        tabela_md(['Status', 'Registros', 'Proporção da base'], [[s, n, percentual(n / len(linhas))] for s, n in qualidade['distribuicao_status'].items()]),
        '`Finished` indica que terminou; `Lapped`, que terminou com volta(s) de atraso; `Retired`, abandono; `Did not start`, não largada; `Disqualified`, desclassificação. Uma posição numérica não basta para concluir que o piloto completou a prova. Mantivemos os status e não usamos o resultado ou o status final para escolher favoritos.',
        '## 3. Frequência de pódio por posição de largada',
        'Frequência observada = registros de pódio naquela posição / todos os registros daquela posição. Os denominadores incluem não largadas, abandonos e desclassificações: são posições de grid **registradas na fonte**, não uma contagem de largadas efetivas. O indicador `podio` é 1 exatamente quando a posição final está entre 1 e 3; não depende de pontos ou status.',
        '![Frequência por grid](frequencia_grid.svg)',
        tabela_md(['Grid registrado', 'Registros (n)', 'Pódios', 'Pódios / n'], [[r['grid'] if r['grid'] else '0 — pit lane', r['registros'], r['podios'], percentual(r['proporcao'])] for r in frequencias]),
        '### Grid zero, separado',
        'A documentação Jolpica descreve `grid` e remete à documentação Ergast para lacunas. No contrato original, **zero indica largada do pit lane**, não uma posição melhor que a pole. Nesta extração o único zero é Ocon no México; a notícia oficial da F1 confirma a largada do pit lane. Um único registro não permite estimar uma chance confiável para todas as largadas do pit lane. Não recodificamos outros valores nem presumimos que todo caso real de pit lane esteja codificado como zero na fonte.',
        '## 4. Quanto do pódio veio do top 3 do grid?',
        '**{}/{} pódios = {}** vieram de pilotos com grid registrado 1, 2 ou 3. O denominador aqui é o total de vagas no pódio, não o total de pilotos da temporada.'.format(resumo['podios_top3_grid'], resumo['total_podios'], percentual(resumo['proporcao_podios_top3_grid'])),
        '## 5. Referência retrospectiva: escolher grid 1, 2 e 3',
        'Escolhemos os pilotos unicamente pelo grid registrado, inclusive se depois abandonaram, não largaram ou foram desclassificados. Comparamos identificadores de pilotos como conjuntos: a ordem de chegada não afeta o número de acertos. Não substituímos um favorito por outro depois de observar o resultado.',
        '**Média: {} acertos / {} corridas avaliáveis = {} de 3 por corrida.** Os três integrantes corretos ocorreram em **{}/{} corridas = {}**.'.format(soma_acertos, validas, formatar_media(resumo['media_acertos']), resumo['distribuicao_acertos']['3'], validas, percentual(resumo['proporcao_tres_corretos'])),
        '![Acertos por corrida](acertos_por_corrida.svg)',
        '![Distribuição dos acertos](distribuicao_acertos.svg)',
        tabela_md(['Acertos (sem ordem)', 'Corridas', 'Proporção das avaliáveis'], [[i, resumo['distribuicao_acertos'][str(i)], percentual(resumo['distribuicao_acertos'][str(i)] / validas) if validas else 'n/d'] for i in range(4)]),
        '### Escolhidos e pódio real em cada corrida',
        tabela_md(['Rodada', 'Corrida', 'Escolhidos (ordem do grid)', 'Pódio real (ordem final)', 'Acertos / 3', 'Problemas do grid'], [[a['rodada'], a['corrida'], '; '.join(r['piloto'] for r in a['escolhidos']), '; '.join(r['piloto'] for r in a['podio_real']), a['acertos'] if a['avaliavel'] else 'não avaliável', '; '.join(a['problemas_grid']) or 'nenhum'] for a in avaliacoes]),
        'Se faltar uma posição necessária ou houver duplicação em grid 1, 2 ou 3, a corrida fica sinalizada como não avaliável, sem escolher arbitrariamente entre pilotos. Ela não entra na média, distribuição ou taxa de três acertos; o número excluído e os denominadores são explícitos. Nesta base: {} corrida(s) não avaliável(is). O CSV da avaliação inclui IDs, além dos nomes.'.format(resumo['corridas_nao_avaliaveis']),
        '### Maior e menor correspondência',
        '**Maior:** {}. **Menor:** {}.'.format(maiores, menores),
    ]
    for a in avaliacoes:
        if a['circuito_id'] == 'interlagos' and a['avaliavel']:
            iguais = resumo['distribuicao_acertos'][str(a['acertos'])]
            textos += ['## 6. São Paulo: comum ou incomum?',
                       'São Paulo teve **{} de 3 acertos**. Esse nível de correspondência ocorreu em **{}/{} corridas ({})**. Assim, foi um caso incomum **descritivamente nesta temporada**, não uma prova estatística de que o circuito sempre será imprevisível.'.format(a['acertos'], iguais, validas, percentual(iguais / validas))]
    textos += [
        '## 7. Observações, hipóteses e limitações',
        '- **Observações:** as contagens, frequências e coincidências das tabelas são verificáveis nos JSON originais. Grid 1 e 2, por exemplo, podem ser comparados com os demais usando os numeradores e denominadores acima. São Paulo tem a menor correspondência observada nesta base.',
        '- **Hipóteses explicativas:** ritmo, estratégia, chuva, acidentes ou características do circuito podem influenciar a relação entre grid e pódio. Estas tabelas não testam essas causas; não atribuímos o resultado de São Paulo a uma delas sem dados adicionais.',
        '- Associação não demonstra causalidade: pilotos e equipes mais fortes podem tanto largar na frente quanto terminar no pódio. Há pilotos repetidos e dependência entre resultados; as linhas não são experimentos independentes.',
        '- São apenas 24 corridas de uma temporada. Frequências empíricas, principalmente com poucas ocorrências e zeros, não são probabilidades calibradas de um modelo. Não generalizamos 2024 para todas as temporadas.',
        '- A referência é **retrospectiva**, baseada no grid registrado nos resultados finais. Não equivale a uma previsão registrada logo após a classificação: penalidades, trocas de componentes e mudanças de grid podem ocorrer depois. Não usamos uma fotografia temporal do grid naquele momento.',
        '- Confiamos nos campos da fonte e preservamos seu significado e status. Revisões posteriores da API não aparecem automaticamente no cache. A completude é relativa ao calendário e total fornecidos pela API, não uma auditoria independente de todos os documentos esportivos.',
        '- Pontos são os da corrida principal neste endpoint; não são uma tabela de pontuação total de pilotos com sprints.',
        '## 8. O que um futuro modelo tentará superar',
        'O primeiro alvo de comparação será superar a **média de {} acertos de 3** e acompanhar a taxa de três integrantes corretos (**{}**) desta regra simples. Comparações justas exigem dados não usados para ajustar o modelo, mesma definição de pódio, mesmos participantes e o mesmo instante de disponibilidade das informações. Superar esses números nos próprios dados de treino não demonstraria capacidade de previsão. Um modelo de probabilidades também precisará avaliar calibração e erros probabilísticos, algo que esta regra de seleção não mede.'.format(formatar_media(resumo['media_acertos']), percentual(resumo['proporcao_tres_corretos'])),
        '## 9. Fontes e atribuição',
        '\n'.join('- [{}]({})'.format(titulo, url) for titulo, url in fontes),
        'Dados: Jolpica-F1, CC BY-NC-SA 4.0. Transformações: seleção de campos, agregação e gráficos. Projeto educacional não comercial, sem vínculo oficial com a Fórmula 1. Preserve a atribuição/licença ao redistribuir os dados e consulte os termos antes de outros usos.',
    ]
    figuras = {}
    figuras['frequencia_grid.svg'] = grafico_barras(
        'Com que frequência cada posição chegou ao pódio?',
        'Corridas principais de 2024 · registros no pódio / registros no grid · sem excluir status',
        [('Grid {}'.format(r['grid']) if r['grid'] else '0 — pit lane (categoria separada)', r['proporcao'], '{}/{} = {}'.format(r['podios'], r['registros'], percentual(r['proporcao'])), '#cc8a16' if not r['grid'] else '#148c87') for r in frequencias],
        1, [(i / 4, '{}%'.format(25 * i)) for i in range(5)],
        'Fonte: Jolpica-F1 · dados CC BY-NC-SA 4.0 · zero observado não significa impossibilidade futura.')
    figuras['acertos_por_corrida.svg'] = grafico_barras(
        'Grid 1, 2 e 3: quantos pilotos coincidiram com o pódio?',
        'Comparação de integrantes, sem considerar ordem · não é uma previsão registrada antes da corrida',
        [('{:02d} · {}'.format(int(a['rodada']), a['corrida'].replace(' Grand Prix', '')), a['acertos'], '{}/3'.format(a['acertos']) if a['avaliavel'] else 'não avaliável', '#cc8a16' if a['circuito_id'] == 'interlagos' else '#3275bd') for a in avaliacoes],
        3, [(i, str(i)) for i in range(4)], 'Escolha exclusivamente pelo grid da fonte, sem filtro retrospectivo por resultado ou status.')
    figuras['distribuicao_acertos.svg'] = grafico_barras(
        'Distribuição de acertos da regra simples',
        '{} corridas avaliáveis · média {} de 3 · três corretos: {}'.format(validas, formatar_media(resumo['media_acertos']), percentual(resumo['proporcao_tres_corretos'])),
        [('{} acerto(s)'.format(i), resumo['distribuicao_acertos'][str(i)], '{}/{} corridas = {}'.format(resumo['distribuicao_acertos'][str(i)], validas, percentual(resumo['distribuicao_acertos'][str(i)] / validas) if validas else 'n/d'), '#cc8a16' if i == 0 else '#148c87') for i in range(4)],
        max(validas, 1), [(validas * i / 4, '{:g}'.format(validas * i / 4)) for i in range(5)],
        'Frequência de corridas, não de pilotos · denominador inclui apenas corridas com grid 1, 2 e 3 únicos.')
    freq_csv = [dict(grid=r['grid'], registros=r['registros'], podios=r['podios'], proporcao='' if r['proporcao'] is None else r['proporcao']) for r in frequencias]
    por_corrida = [dict(temporada=a['temporada'], rodada=a['rodada'], corrida=a['corrida'],
                       escolhidos_ids=';'.join(r['piloto_id'] for r in a['escolhidos']),
                       escolhidos_nomes=';'.join(r['piloto'] for r in a['escolhidos']),
                       podio_ids=';'.join(r['piloto_id'] for r in a['podio_real']),
                       podio_nomes=';'.join(r['piloto'] for r in a['podio_real']),
                       acertos=a['acertos'] if a['avaliavel'] else '', avaliavel='1' if a['avaliavel'] else '0',
                       problemas_grid=';'.join(a['problemas_grid'])) for a in avaliacoes]
    arquivos = dict(figuras)
    arquivos.update({
        'relatorio.md': '\n\n'.join(textos) + '\n',
        'resumo.json': json.dumps(resumo, ensure_ascii=False, indent=2) + '\n',
        'frequencia_grid.csv': csv_texto(['grid', 'registros', 'podios', 'proporcao'], freq_csv),
        'avaliacao_por_corrida.csv': csv_texto(list(por_corrida[0]), por_corrida),
        'previa.html': '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pitwall Lab — 2024</title><style>main{width:1100px;max-width:100%}svg{display:block;width:100%;height:auto}</style></head><body><main>' + figuras['frequencia_grid.svg'] + figuras['distribuicao_acertos.svg'] + figuras['acertos_por_corrida.svg'] + '</main></body></html>\n',
    })
    for nome, texto in arquivos.items():
        destino = saida / nome
        if destino.exists() and destino.read_bytes() != texto.encode('utf-8'):
            raise FileExistsError('Relatório existente diferente: {}. Preserve-o em backup antes de regenerar.'.format(destino))
    for nome, texto in arquivos.items():
        salvar_preservando(saida / nome, texto)
    print('ANÁLISE COMPLETA: {} registros, {} corridas; média {} acertos; {}/{} pódios vieram do top 3 do grid.'.format(len(linhas), resumo['corridas'], formatar_media(resumo['media_acertos']), resumo['podios_top3_grid'], resumo['total_podios']))
    print('Relatório: {}'.format(saida / 'relatorio.md'))
    return resumo


if __name__ == '__main__':
    try:
        gerar()
    except (OSError, ValueError) as erro:
        print('Falha na análise: {}. Nenhum dado parcial foi tratado como completo.'.format(erro), file=sys.stderr)
        sys.exit(1)
