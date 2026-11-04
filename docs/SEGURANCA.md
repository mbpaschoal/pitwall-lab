# Segurança do Pitwall Lab

Português · [English](en/SECURITY.md)

## Superfície e limites

O dashboard público apresenta artefatos locais. Não precisa de secrets para navegar e não coleta, treina ou executa inferência a pedido do visitante. Isso reduz a superfície de ataque, mas bibliotecas, componentes HTML, hospedagem, contas e automações ainda podem ter falhas. Testes de produto, hashes e scanners são evidências complementares; nenhum deles comprova ausência de vulnerabilidades ou de incidentes.

O exportador permite apenas arquivos explícitos, rejeita caminhos indevidos e links simbólicos, e produz inventário/manifesto com SHA-256. O verificador compara a árvore real, hashes e baseline científico. Esses controles ajudam contra divergências e publicação acidental; não substituem controle de acesso, pois alguém com escrita suficiente poderia modificar arquivos e manifesto juntos.

## Código e automação

- Actions usam o SHA completo de uma revisão conferida. O checkout não mantém credenciais no Git.
- A permissão padrão do token é somente leitura. Os jobs de release, coleta e manutenção declaram as permissões adicionais necessárias. A coleta ainda precisa escrever conteúdo e despachar sua recuperação; essa capacidade residual não é apresentada como eliminada.
- O job de coleta aceita somente `main` do repositório oficial. A manutenção disparada por outro workflow sempre lê `main`, nunca o código do evento que a disparou. PRs não recebem os tokens de escrita desses jobs.
- O Git usa a autenticação do CLI somente na etapa de publicação, sem token gravado no checkout. Publicação continua atômica, sem force push, e recuperação usa fonte nova e capturas preservadas.
- O CI de produto chama o workflow de segurança; a release depende dos testes de produto, navegador e segurança. Auditoria diária também pode falhar e exige tratamento pelo mantenedor.
- `scripts/security/check_workflows.py` e suas contraprovas bloqueiam referências móveis de Actions, credenciais persistidas, permissões inesperadas e mistura de código não confiável com jobs privilegiados.

## Dependências e segredos

A apresentação usa Python 3.12 em ambiente próprio. A entrega 0.8.30 atualiza Streamlit, Protobuf, PyArrow e Pillow para versões sem os alertas encontrados na auditoria desta entrega. `requirements_modelo_v1.txt`, a `.venv` científica, modelo e previsões anteriores não são atualizados por esse trabalho.

`pip-audit --strict` resolve e audita dependências diretas/transitivas da apresentação e da receita científica. Uma consulta que falha não vira resultado limpo; novos alertas fazem a verificação falhar. Dependabot propõe PRs semanais de apresentação e Actions, sem auto-merge. Uma proposta não está pronta para publicação até ter versão, changelog, pacote regenerado e verificações aprovadas. A receita científica congelada é auditada, mas não recebe atualização automática.

Gitleaks é baixado de uma release oficial fixada, com checksum conferido, e examina o histórico com valores ocultos. `.gitleaksignore` contém somente cinco fingerprints históricos revisados: identificadores de controles em testes e checksums de artefatos. Não há exclusão de pastas ou regras inteiras. Novas ocorrências exigem investigação; se forem credenciais reais, revogue/rotacione primeiro e avalie o alcance antes de tratar o histórico. Não publique credenciais nem relatórios sem ocultação.

## Configurações administrativas e conta

Secret scanning, proteção de push, Dependabot, CodeQL, relatos privados e regras de branch são configurações do GitHub. Sua ativação precisa ser conferida na API ou na interface; a presença deste documento não comprova que estejam ativas. A política versionada em `scripts/security/` descreve as regras pretendidas; o recibo da entrega registra o que a API realmente confirmou.

`gh-secure` é auxiliar de configuração, instalado por revisão fixada. Use `gh secure status --repo mbpaschoal/pitwall-lab` e simulação antes de mudar recursos. Há regras separadas sem exceções contra exclusão/force push da `main` e contra alteração/exclusão de tags `v*`. Neste repositório pessoal, o GitHub recusou usar o bot nativo Actions como exceção a uma regra de PR obrigatório. Para preservar a publicação atômica sem introduzir uma chave adicional, a main não exige PR pela plataforma; o mantenedor integra mudanças de código por PR e os workflows bloqueiam releases sem as verificações. A automação audita política, dependências, histórico e alterações novas antes de publicar; uma falha preserva as capturas. Exigir PR obrigatório com uma exceção estreita depende de um GitHub App próprio instalado e de autorização específica. As regras de `main` são adaptadas à publicação automática: não aplique cegamente a política genérica de uma aprovação obrigatória. Não amplie permissões de uma credencial só para obter um indicador verde.

O proprietário deve manter 2FA/passkeys, códigos de recuperação guardados fora do repositório, revisar sessões/aplicativos/chaves e acessos do GitHub e Streamlit. Configurar senha, 2FA ou passkeys exige participação do proprietário. Não registre códigos, tokens, cookies ou callbacks em relatórios. Git remoto, Dropbox e caches de Actions não substituem uma cópia de segurança independente com restauração testada.

## Relato e resposta

Use o [canal privado](https://github.com/mbpaschoal/pitwall-lab/security/advisories/new), conforme [SECURITY.md](../SECURITY.md). Em suspeita de comprometimento: preserve evidências sem segredos, revogue credenciais afetadas, interrompa a automação comprometida se necessário, restaure uma versão verificada e confira dados/releases antes de retomar. Não reescreva probabilidades ou evidências científicas para esconder uma divergência.
