# n8n dependency provenance and remaining finding

Created by: MBPaschoal
Status: restricted local deployment; residual Zod advisory open
Type: dependency provenance and operational decision
Date: 2026-11-05

## Português

O pacote npm n8n 2.46.6, instalado como dependência de outro projeto, não aplica automaticamente os overrides do monorepo de origem. A primeira auditoria desse grafo encontrou 4 alertas críticos, 57 altos, 68 moderados e 7 baixos. Isso é um resultado do scanner sobre versões instaladas, não evidência de exploração. Os recibos da primeira instalação permanecem históricos; o aceite operacional não significava auditoria completa das dependências.

Os overrides foram derivados de [n8n-io/n8n, revisão 7a1577667ead44c456b8353f05339045f0a4c006](https://github.com/n8n-io/n8n/blob/7a1577667ead44c456b8353f05339045f0a4c006/pnpm-workspace.yaml), resolvendo seus catálogos em valores explícitos. Autores: n8n-io e contribuidores; [licença da origem](https://github.com/n8n-io/n8n/blob/7a1577667ead44c456b8353f05339045f0a4c006/LICENSE.md). A configuração derivada preserva essa proveniência; não redistribui o servidor n8n nem amplia a licença de terceiros.

Foram acrescentadas correções posteriores ao catálogo para `markdown-it` 14.3.3, MCP SDK 1.32.0/node 2.1.0, `toml` 5.0.1, MSAL Node 7.1.0, `body-parser` 2.4.0 e `follow-redirects` 1.16.2. Os manifestos e integridades vêm do registro oficial npm; o lockfile fixa os bytes. A validação de compatibilidade cobre somente os três nós desta implantação, não todas as integrações opcionais do n8n.

**Permanece aberto [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5), no Zod 3.25.76.** O upstream mantém Zod 3; substituir globalmente por Zod 4 seria mudança de contrato não validada. A decisão local do Codex é manter a versão compatível e registrar o risco de consumo de memória. Mitigações verificáveis: interface somente em 127.0.0.1; payload recebido limitado a 1 MiB; somente Manual Trigger, Schedule Trigger e HTTP Request; nenhum código arbitrário, pacote Community adicional, credencial externa ou webhook público configurado. O workflow recebe apenas configuração fixa e consulta a ponte local. Isso reduz a exposição e não corrige o Zod nem prova ausência de exploração possível. Não usar esse aceite para expor o servidor na internet ou ampliar seus nós.

`audit_result.py` bloqueia críticos e qualquer alto diferente desse advisory/versão exatos. A exceção exige o perfil local acima. Alertas moderados/baixos continuam visíveis no recibo; não são convertidos em zero. Falha de rede ou auditoria incompleta bloqueia a etapa. O CI conserva o relatório bruto e o resultado da política. Nenhum pacote é corrigido automaticamente pela rotina agendada.

## English

Installing the published npm dependency does not inherit n8n's monorepo overrides. This deployment resolves the upstream catalog into explicit overrides, adds the listed advisory patches and locks dependency bytes. Only the three-node coordinator workflow is compatibility-tested.

Zod 3.25.76 retains an open high-severity memory-exhaustion advisory. A global Zod 4 migration is not assumed compatible. The scoped operational decision requires loopback binding, a 1 MiB incoming payload cap, exactly three node types, no additional Community packages and no external credentials or public webhooks. These are mitigations, not a vulnerability fix. The audit gate rejects critical findings, any other high advisory/version and incomplete reports. Moderate/low findings remain visible. This profile must not be reused for a public n8n server or expanded node set without review.
