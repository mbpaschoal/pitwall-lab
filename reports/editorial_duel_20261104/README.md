# Acabamento editorial e Duelo — 0.10.0

Created by: MBPaschoal

Status: implementação e validação local concluídas; CI e publicação pendentes

Type: evidência de entrega

Primeira etapa da evolução aprovada: acabamento visual, respostas aos comandos e Duelo. Paleta, fontes e fotografias preservadas. O novo Duelo mantém métricas nativas, retratos lado a lado e uma diferença legível na métrica selecionada, sem misturar o placar de posições com vitórias/pódios. Taxas usam pontos percentuais; contagens usam inteiros. Empates, amostras insuficientes e ausência de largadas em comum ficam explícitos.

## Evidência local

- 78 testes focais e 146 portáteis: aprovados. [Log focal](focused-final.txt), [log portátil](portable-final.txt).
- [Chromium](package-chromium/editorial.json) e [WebKit](package-webkit/editorial.json): quatro contextos cada, PT/EN em 390/1440 CSS px. Mudança real de condição/métrica, denominadores, mínimo, ausência, duas trocas de idioma e movimento reduzido manual/pelo sistema. O oráculo conta diretamente os resultados-fonte.
- 24 casos de controles no WebKit: [recibo](controls-webkit/controls.json). As varreduras de rolagem dos dois motores examinam as seis telas, cinco posições de rolagem e situações de texto ampliado/janela curta; zero problemas registrados.
- [Pacote e ZIP](package.json): 483 membros verificados individualmente, versão e build identificados. Pacote anterior preservado fora do checkout; substituição canônica restrita aos dez arquivos esperados.
- [Preservação](preservation.json): 373 caminhos científicos, de dados e de operação sem alteração. O [inventário original](protected-before.json) inclui também o manifesto gerado e o catálogo EN da distribuição, cuja alteração de apresentação é explicitamente permitida. Baseline científico mantido.
- Política de workflow e 18 pares de documentos PT/EN aprovados. Nenhum coletor, treino ou inferência executado. Celular emulado.

## Falhas de ferramentas preservadas

A primeira geração de recibo tentou usar `hashlib.file_digest` no Python 3.9 padrão e falhou depois de copiar e comparar os membros do pacote. A conferência foi refeita no ambiente de apresentação Python 3.12 existente. [Registro](sync-receipt-first-failure.txt). A primeira comparação ampla do inventário JSON também sinalizou os dois arquivos de apresentação esperados; o inventário original permanece intacto, e a exceção final admite somente os dois caminhos explícitos. [Registro](preservation-check-first.txt).

## Publicação

Pendente de CI e versão/build realmente servidos. Uma validação local não demonstra implantação pública.

## English

Phase one implements editorial polish, command feedback and an enhanced existing driver duel. All local focused/portable tests and PT/EN desktop/mobile-emulated duel contexts passed. The metric difference uses percentage points for rates, integers for counts and explicit tie/insufficient-sample states. Frozen scientific artefacts and recorded predictions remain unchanged. CI and public deployment are pending and must be confirmed separately. Tooling failures and the original inventory are retained.
