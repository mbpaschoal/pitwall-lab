# Pitwall Lab

Português · [English](README.en.md)

[**Abrir dashboard público**](https://pitwall-lab.streamlit.app/)

Portfólio de MBPaschoal sobre ciência de dados na Fórmula 1. Este pacote apresenta probabilidades individuais de pódio, evidências e limitações. Não estima a ordem P1/P2/P3 nem consulta APIs durante a navegação.

## Produto

- **Pilotos:** destaques por condição, perfil individual, amostra mínima, empates e evidências de cada GP.
- **Corridas:** circuito, campeonatos completos, tempos, pneus/paradas, clima, equipes e até cinco edições anteriores na mesma pista.
- **Previsões:** probabilidades registradas e comparação posterior, com Austin prospectivo separado da retrospectiva.
- **Desempenho:** métricas, calibração e cobertura explícita.
- **Metodologia:** documentos e relatórios offline, também em inglês.

As bandeiras BR/GB no canto superior direito selecionam o idioma. A navegação preserva temporada, GP e idioma. Identificadores e downloads científicos conservam seus bytes originais; tabelas descritivas acompanham o idioma.

## Evidência e aprendizado

Modelo v1 congelado: treino 2021–2023, validação 2024 já explorada e 2025 já avaliado. Nos mesmos 22 GPs de ranking de 2025, o modelo identificou 51 integrantes de pódio contra 50 da classificação; ambos acertaram três em 8/22 GPs. Métricas probabilísticas usam 478 casos. Isso não demonstra significância nem garantia futura.

Pilotos cruza 66 corridas principais e 1.340 largadas com sensores nos intervalos efetivos e mapas FIA de cada edição. São oito provas com chuva registrada. A auditoria registra 295 verificações; 17 compostos de treinos/classificação continuam ausentes e não entram nesses rankings. O clima distingue sensores da corrida e reconstrução atmosférica horária. Baku/Q mantém o complemento FIA sem setores/validade inventados.

A correção do Histórico mostrou que uma tabela pode existir e responder à pergunta errada. A verificação de publicação passou a conferir o build servido porque testes locais não provam deploy. [Evolução e versões](CHANGELOG.md).

## Executar

Use Python 3.12 num ambiente novo dentro deste pacote; isso não modifica o ambiente científico original:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

A implementação está em `pitwall/dashboard`, `pitwall/data` e `pitwall/i18n`; módulos da raiz são compatibilidade. Não há modelos joblib, treino, inferência ou dados brutos neste pacote. [Hospedagem](GUIA_HOSPEDAGEM.md), [fontes](FONTES_E_DADOS.md), [licença do código](LICENCA_CODIGO.md).

A versão em `VERSION` é do produto, independente do modelo v1 e do build registrado em `MANIFESTO.json`. Cada entrega de dados ou melhoria exige nova versão e notas PT/EN. Projeto educacional independente, sem vínculo oficial com Fórmula 1.
