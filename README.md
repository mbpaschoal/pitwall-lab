# Pitwall Lab

**Português · [English](README.en.md)**

Portfólio de ciência de dados sobre Fórmula 1, criado por **MBPaschoal**. Estou aprendendo a construir um produto completo: coletar dados, reconhecer suas limitações, avaliar um modelo e transformar os resultados numa interface compreensível. As correções e os resultados inconclusivos fazem parte desse percurso.

**[Abrir o dashboard](https://pitwall-lab.streamlit.app/) · [Evolução e aprendizados](docs/APRENDIZADOS.md) · [Versões](CHANGELOG.md) · [Arquitetura](docs/ARQUITETURA.md)**

Quem ganha mais na chuva? Como dois pilotos se saem nos mesmos GPs? Quem já foi bem nesta pista? Explore essas perguntas nos filtros; carro e época também influenciam os resultados.

![Pilotos: comparações históricas por condição](docs/images/pitwall-pilotos.png)


Preparação do México 2026: acompanhamento das cinco sessões, fontes e horários explícitos, coleta após encerramento observado e clima previsto separado das medições da corrida. [Operação e limites](docs/OPERACAO_FIM_SEMANA.md). A publicação atual ainda não contém resultados nem previsão prospectiva do México.

## O produto hoje

- **Pilotos:** destaques por condição, perfil, duelos, favorito no navegador e cartões para compartilhar. Filtros, amostras e empates ficam explícitos. [Auditoria dos dados](reports/pilotos_condicoes_20261029/README.md).
- **Corridas:** resultado, ficha do circuito, tempos, clima, pneus/paradas, equipes e desempenho dos pilotos em até cinco edições anteriores na mesma pista.
- **Campeonato:** classificação completa de pilotos e equipes na rodada selecionada.
- **Chances de pódio:** probabilidades individuais de pódio e comparação posterior. A emissão prospectiva de Austin 2026 permanece separada do estudo retrospectivo.
- **Acertos do Lab:** log loss, Brier, calibração, ranking e cobertura, com denominadores explícitos.
- **Como funciona:** documentos e relatórios offline. As bandeiras 🇧🇷 e 🇬🇧 no canto superior direito selecionam português ou inglês e acompanham a navegação.

O acervo descritivo cobre **66 GPs e 330 sessões de 2024–2026 até Austin**. Pilotos usa 1.340 largadas, sensores nos intervalos efetivos e mapas FIA de cada edição. A auditoria registra 295 verificações; 17 compostos de treinos/classificação continuam ausentes e não entram nesses rankings. O Histórico compara edições anteriores da mesma pista. [Correções e limites](docs/DADOS_ATUAIS.md).

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

Dados de fontes diferentes conservam suas próprias condições; nenhuma licença é estendida automaticamente a outra fonte. O código original está sob a [licença MIT](LICENSE); os materiais de terceiros mantêm seus próprios termos. Projeto educacional independente, sem vínculo oficial com Fórmula 1, fontes ou equipes.

- [Entrega dos 45 itens da revisão crítica](docs/REVISAO_030.md)
