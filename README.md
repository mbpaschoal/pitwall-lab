# Pitwall Lab

Portfólio público de ciência de dados sobre Fórmula 1. O projeto apresenta um
estudo retrospectivo de probabilidades individuais de pódio, com fontes,
limitações e separação temporal documentadas. Não é uma previsão ao vivo e não
estima a ordem P1/P2/P3.

**[Abrir dashboard público](https://pitwall-lab.streamlit.app/)**

## O que está disponível

- Dashboard Streamlit com as telas **Corridas**, **Previsões**, **Desempenho** e
  **Metodologia**.
- Artefatos locais para 2024 e 2025; 2024 foi validação já explorada e 2025 foi
  avaliação retrospectiva já realizada.
- Operação 2026 separada do histórico: classificação oficial de pilotos vem de
  um snapshot paginado de `DriverStandings` da Jolpica-F1; probabilidades são
  exibidas somente para o GP da emissão correspondente.
- Austin 2026 tem uma **previsão registrada** congelada antes da corrida e o
  resultado posterior validado localmente. A interface preserva as probabilidades
  originais e mostra a auditoria pós-corrida separada do estudo retrospectivo.
- Interface editorial compartilhada por 2024–2026, com fontes locais, busca na
  temporada, preferências da sessão e composição responsiva. O CSS está em
  `frontend_assets/pitwall.css`; `pitwall_ui.py` controla a grade e
  `pitwall_ui_dados.py` fornece apenas contexto descritivo validado. Austin usa
  uma ilustração identificada como IA e os campeonatos oficiais de pilotos e
  construtores pós-GP. Dados indisponíveis aparecem como lacunas, sem copiar os
  números ilustrativos da referência visual.

## Limites importantes

As probabilidades são individuais e não somam obrigatoriamente três por GP. A
avaliação é retrospectiva: fontes podem ter sido revisadas após as datas dos
eventos, e os resultados de 2024/2025 não demonstram desempenho futuro.

A classificação de pilotos de 2026 e as probabilidades por GP são blocos
independentes. O estudo não reutiliza a emissão retrospectiva de Singapura para
Austin nem transforma ausência de dados em zero, favoritos ou previsão.

## Executar localmente

O dashboard local usa o ambiente virtual já existente no projeto:

```bash
./.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Abra `http://127.0.0.1:8501`. O aplicativo não coleta dados, não treina o
modelo e não faz inferência durante a visualização.

## Publicação gratuita no Streamlit Community Cloud

A entrega portátil pronta para hospedagem está em
[`distribuicao/pitwall-dashboard/`](distribuicao/pitwall-dashboard/README.md).
Ela contém seu próprio `app.py`, `requirements.txt`, configuração Streamlit e
inventário de arquivos publicáveis.

O aplicativo público está em **https://pitwall-lab.streamlit.app/**. Para
atualizar a publicação no Streamlit Community Cloud, selecione a branch `main`
e o entrypoint:

```text
distribuicao/pitwall-dashboard/app.py
```

Em **Advanced settings**, escolha Python 3.12. O `requirements.txt` fica no
mesmo diretório do entrypoint e não há secrets necessários. O passo a passo e
as limitações estão em
[`distribuicao/pitwall-dashboard/GUIA_HOSPEDAGEM.md`](distribuicao/pitwall-dashboard/GUIA_HOSPEDAGEM.md).

## Documentação técnica

- [Protocolo temporal](docs/protocolo_temporal.md)
- [Experimento do modelo v1](docs/experimento_modelo_v1.md)
- [Avaliação final retrospectiva](docs/avaliacao_final_v1.md)
- [Dicionário de variáveis](docs/dicionario_variaveis.md)
- [Fontes e condições dos dados](docs/fontes_operacao_2026.md)

## Fontes e atribuição

Os dados históricos e operacionais usados pelo projeto derivam de Jolpica-F1.
Consulte os documentos de fonte e de limitações antes de reutilizar os dados.
Os dados seguem as condições informadas pela fonte, incluindo CC BY-NC-SA 4.0;
a licença do código permanece uma decisão separada do autor.

Projeto educacional independente, sem vínculo oficial com a Fórmula 1.
