# Política de versões do produto

Português · [English](en/VERSIONS.md)

`VERSION` é a fonte da versão do Pitwall Lab. Modelo v1, pesquisa v2, snapshots e build têm identificadores separados. A primeira versão formal é **0.1.0**; commits anteriores são marcos históricos reais, sem versões inventadas.

| Mudança entregue | Incremento |
|---|---|
| Novos dados, correção de dados, texto ou bug compatível | PATCH: `0.1.0 → 0.1.1` |
| Nova funcionalidade compatível | MINOR: `0.1.0 → 0.2.0` |
| Quebra de contrato público ou formato incompatível | MAJOR: `0.1.0 → 1.0.0` |

Durante 0.x, mudanças incompatíveis continuam explicitadas e revisadas; não escondê-las num patch. Várias alterações da mesma entrega podem compartilhar uma versão; cada nova entrega exige outra versão. Atualizar dados não significa retreinar o modelo. Não agendar coleta nem criar releases vazias automaticamente.

Cada entrega exige:

1. Atualizar `VERSION`, `CHANGELOG.md` e `CHANGELOG.en.md`.
2. Escrever problema anterior, comportamento entregue, testes/evidências e aprendizado/limite nos dois idiomas.
3. Verificar os artefatos congelados, tradução e pacote pertinente.
4. Criar commit(s) com assunto claro e corpo PT/EN, sem alterar o histórico anterior.
5. Criar tag `vX.Y.Z` para o commit real da entrega. As notas da release são extraídas da seção correspondente dos changelogs, sem inventar resultados.
6. Conferir a versão/build servido antes de registrar publicação pública. Uma tag não prova deploy.

O comando `python -m pitwall.publishing.releases check` confere versão, notas e traduções obrigatórias. `notes --language pt|en` produz as notas da versão atual. `check --base REF` exige incremento quando código ou dados publicáveis mudam em relação à referência. Correções apenas de documentação podem acompanhar uma versão; mudanças de produto/dados não podem ficar sem incremento.
