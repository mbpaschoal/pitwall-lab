# Entrega da revisão crítica — 0.3.0

[English](en/REVIEW_030.md)

2026-10-29

Os 45 itens aprovados estão mapeados abaixo. O aceite final inclui testes da raiz, pacote isolado e navegador real. O modelo v1, suas 15 entradas e as emissões registradas permanecem preservados.

| ID | Implementação |
|---|---|
| A01 | Links preservam os filtros e há retorno ao resumo de pilotos. |
| A02 | Vento usa média circular; zero continua válido. |
| A03 | Referência individual restrita aos GPs com largada do piloto. |
| A04 | Contagens não são comparadas à soma dos demais; duelos usam pares. |
| A05 | Resumo usa temperatura da corrida e ícone neutro, com fonte. |
| A06 | Campeonato identifica a rodada de referência sem afirmar ocorrência futura. |
| A07 | Campos declarados disponíveis são confrontados com valores; contraprova para vento nulo. |
| A08 | CI verifica manifesto, hashes e testes do pacote servido. |
| A09 | Link PT do relatório inglês resolvido dentro do pacote. |
| B01 | Entrada em 2026 no último GP observado; limite Austin explícito. |
| B02 | Pódio e resultado primeiro; campeonato em tela própria. |
| B03 | Chances de pódio, Acertos do Lab e Como funciona. |
| B04 | Busca local entre temporadas, pistas, pilotos e equipes, também em Pilotos. |
| B05 | Filtros globais na lateral; GP oculto quando não se aplica. |
| B06 | Preferências usam ícone de configurações. |
| B07 | Ausência, mínimo, zero sucessos, futuro e não aplicável têm estados distintos. |
| B08 | Perguntas curtas e glossário; método técnico em expander. |
| C01 | Hierarquia serifada compartilhada e escala móvel. |
| C02 | Parágrafos limitados a 75 caracteres aproximados e ritmo de leitura. |
| C03 | Cor auxiliar mais escura, com contraste localizado corrigido. |
| C04 | Pódio antes da imagem; título e pista menores no celular. |
| C05 | Seis abas visíveis em 390 px, sem corte horizontal. |
| C06 | Classificação inteira; equipe junto ao nome no celular. |
| C07 | Filtro do mapa, lacunas distintas de zero e hover em percentual. |
| C08 | Bandeiras com nomes acessíveis, área de toque e decimal por idioma. |
| D01 | Localização sem repetir o GP; nota de emissão fica em Chances. |
| D02 | Cartões sem frase repetida; cada empatado tem seu link e amostra. |
| D03 | Listas iguais viram uma lista e uma observação curta. |
| D04 | Clima da corrida primeiro; fim de semana recolhido. |
| D05 | Exportações em ações secundárias, preservando fontes e CSV. |
| E01 | Perfil com todas as 16 condições selecionáveis. |
| E02 | Vitórias/pódios em corridas; limites e influência de carro/época explícitos. |
| E03 | Destaques calculados, vencedores anteriores e trajetórias recentes/na pista. |
| E04 | Duelo em largadas compartilhadas; abandono e DSQ explicitados; companheiro cobre todas as condições. |
| E05 | Favorito persiste no navegador e recebe destaque no ranking. |
| E06 | URL com contexto e cartão SVG com período, amostra e fonte. |
| E07 | Glossário leve, histórico nesta pista e gráfico de pontos das equipes. |
| F01 | Avaliação extraída para model_views; cálculos, busca, favorito e exportação separados. |
| F02 | Uma fonte, distribuição gerada; ZIP como ativo da release. |
| F03 | Testes direcionados, pacote isolado e jornada real de navegador. |
| F04 | Instalação pública Python 3.12; blueprint identificado como ferramenta local. |
| F05 | Jornadas PT/EN verificadas, catálogo ampliado e downloads científicos preservados. |
| F06 | README com perguntas, capturas PT/EN e diário honesto das correções. |
| F07 | Derivados de 26 fotos: 27,0 MB para 6,5 MB; cache de URI. Abas ainda são construídas pelo Streamlit; não prometemos latência menor. |
| F08 | Licença MIT para código original; condições de terceiros separadas. |

## Limites

O favorito depende do armazenamento permitido pelo navegador e não sincroniza entre dispositivos. As associações não isolam habilidade nem causalidade. Permanecem 17 compostos de treinos/classificação sem fonte; eles não são imputados nem usados nos rankings. A verificação de contraste cobre o achado do relatório, não certifica toda a acessibilidade.

## Verificação reproduzível

`python -B verificar_pacote.py --pacote distribuicao/pitwall-dashboard`

`node tests/browser/aceite_exploracao.cjs http://127.0.0.1:8501 /tmp/pitwall-acceptance`

O segundo comando requer Playwright 1.62.1 e Chromium, em ambiente de desenvolvimento separado. CI executa a jornada contra a distribuição servida. Ciência não é executada por esses comandos.
