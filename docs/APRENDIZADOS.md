# Aprendizado e refinamento do produto

Português · [English](en/LEARNING.md)

Created by: MBPaschoal
Status: active
Type: learning journal

Este registro explica decisões técnicas do projeto; não é uma lista de resultados sempre positivos. Mensagens históricas de commit permanecem no idioma e na data originais. A tabela oferece contexto bilíngue sem reescrever esse histórico.

| Evidência | Problema percebido | Correção e aprendizado |
|---|---|---|
| [Etapa 3](protocolo_temporal.md) | Uma base ordenada por data pode ainda conter revisões posteriores da fonte. | Separar corte conceitual, regra conservadora e aquisição real. Hash comprova bytes, não disponibilidade histórica. |
| [Avaliação 2025](../reports/avaliacao_final_v1/relatorio.md) | A vantagem de um modelo pode parecer maior sem comparar a mesma população. | Denominadores explícitos e a mesma coorte: 51 contra 50 integrantes; empate em 8/22 pódios completos. Não afirmar significância. |
| [8beae28](https://github.com/mbpaschoal/pitwall-lab/commit/8beae28) | O menu lateral ficou difícil de recuperar. | Restaurar o controle nativo e verificar viewport móvel. Estética não substitui navegação utilizável. |
| [128e272](https://github.com/mbpaschoal/pitwall-lab/commit/128e272) | Tempos de Austin não estavam cobertos pela fonte principal. | Integrar uma alternativa com identidade e proveniência, separada da emissão já registrada. |
| [0e97fbc](https://github.com/mbpaschoal/pitwall-lab/commit/0e97fbc) | Painéis duplicados e classificação incompleta prejudicavam a leitura. | Definir uma tela responsável por cada informação e mostrar todas as linhas publicadas. |
| [edca988](https://github.com/mbpaschoal/pitwall-lab/commit/edca988) | Links que funcionavam localmente falharam no contexto do Cloud. | Testar clique real em iframe e nova aba. Push não demonstra deploy. |
| [Revisão dos dados](DADOS_ATUAIS.md) | Histórico respondia sobre a prova atual; avisos de stint eram tratados como lacunas. | Filtrar pela identidade literal da pista e data anterior; separar aviso de qualidade de limites desconhecidos. Preservar ausências reais. |
| [Versão 0.1.0](../CHANGELOG.md) | Código disperso e idioma único dificultavam manutenção e apresentação do portfólio. | Organizar responsabilidades, centralizar tradução offline e manter compatibilidade. Versão do produto e do modelo têm significados distintos. |

## Como registrar a próxima melhoria

Descrever o comportamento anterior com um exemplo concreto, a causa conhecida (ou a incerteza), a mudança entregue, a verificação executada e o que continua limitado. Uma hipótese não vira resultado confirmado. Datas e versões devem corresponder à entrega real; não criar commits antigos fictícios nem editar resultados para contar uma história melhor.

## 0.2.0: comparar exige verificar o denominador

O brainstorm contava chuva em sessões completas e podia selecionar Sprint pelo tipo Race. A auditoria passou a exigir o nome literal da corrida, status de início e fim e exclusão de suspensões. O resultado mudou para oito provas com chuva durante a disputa. Também aprendi a preservar diferenças entre feeds: a numeração de voltas na Austrália/2026 não deve ser corrigida por um deslocamento aplicado a linhas sem vínculo. Taxas agora mostram largadas e empates; fontes incompletas permanecem incompletas. [Evidência e limites](../reports/pilotos_condicoes_20261029/README.md).
