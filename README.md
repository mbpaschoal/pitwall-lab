# Pitwall Lab

**Português · [English](README.en.md)**

Portfólio de ciência de dados sobre Fórmula 1, criado por **MBPaschoal**. Estou aprendendo a construir um produto completo: coletar dados, reconhecer suas limitações, avaliar um modelo e transformar os resultados numa interface compreensível. As correções e os resultados inconclusivos fazem parte desse percurso.

**[Abrir o dashboard](https://pitwall-lab.streamlit.app/) · [Evolução e aprendizados](docs/APRENDIZADOS.md) · [Versões](CHANGELOG.md) · [Arquitetura](docs/ARQUITETURA.md)**

## O produto hoje

- **Corridas:** ficha do circuito, campeonato completo, tempos, clima, pneus/paradas, equipes e desempenho dos pilotos em até cinco edições anteriores na mesma pista.
- **Previsões:** probabilidades individuais de pódio e comparação posterior. A emissão prospectiva de Austin 2026 permanece separada do estudo retrospectivo.
- **Desempenho:** log loss, Brier, calibração, ranking e cobertura, com denominadores explícitos.
- **Metodologia:** documentos e relatórios offline. As bandeiras 🇧🇷 e 🇬🇧 no canto inferior selecionam português ou inglês e acompanham a navegação.

O acervo descritivo cobre **66 GPs e 330 sessões de 2024–2026 até Austin**. A revisão de 29/10 resolveu 75 dos 112 itens da fila; seis ausências foram confirmadas e 31 limitações de pneus permanecem nas fontes. O Histórico exclui a corrida selecionada e outras pistas do mesmo país. Altitude é uma estimativa no ponto do calendário; mapas DRS de referência não certificam todas as configurações históricas.

## O que aprendi com os erros

Um número exibido não basta: preciso explicar de onde veio, quando poderia estar disponível e o que significa. O Histórico inicialmente mostrava a corrida atual; agora responde à pergunta sobre edições anteriores da mesma pista. Rankings incompletos passaram a declarar a ausência, sem criar posições ou pontuações zero. A publicação ganhou uma verificação própria porque um teste local não comprova o que está no Streamlit.

O [diário de evolução](docs/APRENDIZADOS.md) liga cada aprendizado a uma mudança e a uma verificação. Não atribuo versões retroativas nem reescrevo os commits para aparentar um desenvolvimento sem erros.

## Resultado científico e limites

O **modelo v1 está congelado**: regressão logística, treino em 2021–2023, validação de 2024 já explorada e avaliação retrospectiva de 2025 já realizada. Em 2025, nos mesmos 22 GPs avaliáveis, o modelo identificou 51 integrantes do pódio e a classificação 50; ambos acertaram os três em 8/22 GPs. São resultados descritivos, sem demonstração de significância ou garantia futura.

O modelo não prevê a ordem P1/P2/P3. As probabilidades individuais não são forçadas a somar três. Fontes históricas podem conter revisões posteriores ao corte. **2025 não é mais teste intocado**, e a pesquisa v2 ainda não foi promovida. Dados novos de interface não alteram as 15 entradas, o modelo ou as probabilidades registradas.

## Executar e encontrar o código

O ponto de entrada continua sendo `app.py`. A implementação está no pacote [`pitwall/`](pitwall/), separado pelas responsabilidades do blueprint. Os pequenos módulos da raiz preservam imports/comandos existentes; os produtores científicos congelados mantêm seus caminhos originais.

Para usar o ambiente de análise existente:

```bash
./.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Para uma instalação de apresentação independente, use Python 3.12 e as instruções do [pacote portátil](distribuicao/pitwall-dashboard/README.md). A navegação não coleta dados, treina ou executa inferência. O Cloud usa `distribuicao/pitwall-dashboard/app.py` na branch `main`.

## Versões e contribuição

[`VERSION`](VERSION) identifica o produto; **não** é a versão do modelo. Cada atualização de dados ou melhoria entregue exige nova versão, notas em português/inglês e evidências de validação. A política começa em **0.1.0**, sem inventar versões anteriores. Consulte a [política de versões](docs/VERSOES.md) e o [guia de contribuição](CONTRIBUTING.md).

- [Documentação técnica em português e inglês](docs/README.md)
- [Fontes, atribuição e limites](publicacao/templates/FONTES_E_DADOS.md)
- [Método v1](docs/experimento_modelo_v1.md) · [English](docs/en/experimento_modelo_v1.md)
- [Protocolo temporal](docs/protocolo_temporal.md) · [English](docs/en/protocolo_temporal.md)

Dados de fontes diferentes conservam suas próprias condições; nenhuma licença é estendida automaticamente a outra fonte. A licença aberta do código ainda não foi escolhida pelo autor. Projeto educacional independente, sem vínculo oficial com Fórmula 1, fontes ou equipes.
