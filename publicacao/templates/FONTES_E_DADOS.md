# Fontes e dados

## Origem e atribuição

Os dados apresentados derivam de Jolpica-F1, incluindo o legado voluntário do
Ergast. A fonte primária dos termos é:

- https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md
- https://creativecommons.org/licenses/by-nc-sa/4.0/

Conforme esses termos, os dados são disponibilizados sob **CC BY-NC-SA 4.0**
(Atribuição–NãoComercial–CompartilhaIgual). Dê crédito à Jolpica-F1, identifique
alterações, não sugira endosso e preserve as condições NC e SA nos direitos
cabíveis de contribuições derivadas.

## Transformações identificadas

As transformações históricas — junção por identificadores, janelas temporais,
indicadores de ausência, divisão 2021–2025 e modelagem — foram realizadas antes
desta distribuição. Nesta etapa, não houve nova coleta, treinamento, inferência
ou processamento científico: somente apresentação e cópias dos nove artefatos
necessários ao dashboard.

## Limites de uso

Os dados não recebem licença MIT ou Apache por estarem neste pacote. A condição
NãoComercial não autoriza automaticamente todos os usos de portfólio,
recrutamento ou outros contextos com finalidade comercial. O autor deve avaliar
o uso pretendido e, se necessário, contatar admin@jolpi.ca. Isto não é
aconselhamento jurídico.

Os dados são fornecidos sem garantias. Pitwall Lab é um projeto independente,
sem endosso da Jolpica-F1, Ergast, Fórmula 1 ou equipes/pilotos.

## Acervo descritivo de 2024–2026

O arquivo portátil `frontend_assets/acervo_dashboard.json` acrescenta tempos de
sessões, clima, sequências observadas de pneus, paradas, resultados históricos e
comparativos de equipes para 66 GPs, incluindo Austin 2026. É preparado offline;
o aplicativo não consulta as APIs nem carrega dados brutos durante a navegação.

- **OpenF1**: resultados/tempos, voltas, stints e medições meteorológicas da
  pista. [Documentação](https://openf1.org/docs/) e
  [condições](https://openf1.org/), incluindo CC BY-NC-SA 4.0.
- **Open-Meteo e provedores meteorológicos**: reconstrução/modelo atmosférico
  horário na grade próxima ao circuito, sob
  [CC BY 4.0](https://open-meteo.com/en/licence).
  Weather data by [Open-Meteo.com](https://open-meteo.com/).
  Não se trata de temperatura do asfalto ou previsão emitida antes do GP.
- **Jolpica-F1 e fotografia CSV local de origem histórica**: resultados,
  paradas e classificações acumuladas por rodada. A fotografia local conserva
  aquisição desconhecida e divergência entre duas atribuições antigas de URL;
  o pacote não afirma que um publicador específico forneceu esses bytes.

Os dados apresentados são derivados para exibição e preservam fonte e lacunas.
As condições de uma fonte não substituem as de outra. Compostos e stints são
sequências observadas; não demonstram intenção estratégica, combustível,
undercut ou degradação causal. Race e Sprint são mostrados separadamente.

As voltas detalhadas da classificação de Baku 2025 não foram recuperadas nas
fontes consultadas. Seus resultados e tempos agregados estão disponíveis.
Outros campos ausentes ou limites de stint inconsistentes permanecem sinalizados.
Os dados posteriores não alteram as 15 entradas, o modelo ou as probabilidades
registradas. Os nove artefatos científicos anteriores continuam congelados.
