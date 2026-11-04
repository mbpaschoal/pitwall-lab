# Segurança / Security — 04/11/2026

Created by: MBPaschoal
Status: locally validated; administrative state recorded separately
Type: security delivery evidence

## Português

Entrega 0.8.30 preparada em clone independente do GitHub. A cópia de autoria foi preservada; apresentou índices Git inválidos após a falta de espaço, e não foi reparada nem resetada nesta tarefa. Arquivos da árvore de autoria passaram a retornar zero bytes na verificação, incluindo Home, README, VERSION e arquivos Git. A causa não foi determinada; essa árvore não foi recuperada nem deve ser considerada corrigida. A exclusão de `.streamlit/secrets.toml` está implementada no clone independente/publicação.

O GitHub CLI oficial 2.103.3 foi conferido pelo checksum e autenticado como `mbpaschoal`, com credencial no chaveiro do macOS. `gh-secure` foi inspecionado e instalado na revisão `a04d1c144f5d1b63a8aa5cd7946e8ceafa709a2a`. Não foram registrados códigos, tokens, callbacks, cookies ou códigos de recuperação.

Actions fixadas por SHA; checkout sem credenciais persistidas; token padrão somente leitura, com privilégios explícitos nos jobs necessários. Workflow de segurança reutilizado pelo CI e agendado diariamente: política de confiança, auditoria transitiva de duas pilhas e Gitleaks com ocultação de valores. Dependabot não altera automaticamente a receita científica. As duas regras efetivas de integridade de main/tags estão em `scripts/security/`; o estado administrativo está no recibo/API. PR obrigatório com bypass do bot nativo foi recusado pelo GitHub (HTTP 422). A política mantém publicação atômica, bloqueios de force push/exclusão e gates de segurança antes de todas as releases, sem criar uma credencial adicional. A main ainda permite push normal autorizado.

Dependências de apresentação: Streamlit 1.66.1, PyArrow 23.0.1, Protobuf 5.29.6 e Pillow 13.0.0. A versão mais nova de Streamlit é necessária para aceitar Pillow 13 sem violar as restrições do pacote. A instalação transitiva inicial de Pillow 12.3.0 ainda apresentou alertas: o resultado foi preservado na investigação, sem ignorá-los. Os seletores foram adaptados aos controles React Aria e as expectativas AppTest à representação escalar dos parâmetros de URL. Não houve mudança de dados, modelo ou probabilidades.

Rolagem/foco: 120 amostras e 14 cenários de estresse sem ocorrências. Links alternativos: quatro cenários PT/EN desktop/mobile e recuperação tardia dos controles aprovados.

Validação local: 405 testes do CI de produto, sete contraprovas de política, 144 testes portáteis, dez contraprovas do verificador público, 24 cenários Chromium + 24 WebKit e 16 jornadas de contexto. Auditorias: 34 dependências de apresentação e cinco científicas, sem alertas conhecidos na consulta. 300 arquivos científicos protegidos sem alteração. O teste focal de exportação preserva autoria textual após retirar marcação HTML de um crédito legado; continua exigindo autor e licença.

Gitleaks examinou 133 commits e encontrou cinco falsos positivos verificados: duas chaves de widgets e três checksums. Somente seus fingerprints históricos foram isentados. Nova varredura sem achados; isso não certifica ausência de segredos em arquivos privados ou fora do histórico examinado.

2FA já configurado com aplicativo autenticador e GitHub Mobile; proprietário único, sem chaves de deploy nem secrets adicionais de Actions. Nenhuma passkey nova foi criada. Não foi configurado backup independente nem testada sua restauração. Veja [controles e limites](../../docs/SEGURANCA.md).

O primeiro CI hospedado encontrou changelogs do pacote fora de sincronia e incompatibilidades de popovers no Linux. O pacote foi regenerado, o seletor legado passou a ocultar somente o indicador de rádio e o teste fecha o diálogo com Escape; quatro casos de menu e quatro de filtros/idioma foram reconferidos. As execuções iniciais continuam preservadas no histórico do PR. A terceira execução aprovou validação, segurança e navegação, mas encontrou abertura instável do seletor de sessão durante rolagem suave. O teste agora aguarda a posição do campo estabilizar antes de abrir a lista, sem alterar a aplicação nem retirar verificações. Reconferidos oito casos locais de sessões/CSV e pneus/paradas, em PT/EN desktop/mobile; recibos `weekend-sessions-local.json` e `lawson-tyres-local.json`.

CI hospedado, merge, release e verificação do dashboard público têm evidências próprias posteriores; os testes locais acima não comprovam implantação. Consulte o histórico de PRs/Actions e o recibo final da sessão para o estado de publicação.

## English

Release 0.8.30 was prepared in an independent GitHub clone. The authoring checkout was preserved and not reset/repaired after invalid Git indexes appeared following disk exhaustion. Existing authoring files returned zero bytes; their cause and recovery remain unresolved. Streamlit-secret exclusion is implemented in the independent/published checkout, not established for the invalid authoring tree.

The official CLI was checksum-verified; the reviewed gh-secure revision is pinned. Tokens remain in the macOS keychain and are not recorded. Workflows use pinned Actions, non-persistent checkout credentials, read-only default permissions and explicitly scoped privileged jobs. Reusable/daily security checks audit workflow trust boundaries, both dependency stacks and Git history. Dependabot never automatically changes the frozen scientific recipe.

Presentation updates include Streamlit 1.66.1, PyArrow 23.0.1, Protobuf 5.29.6 and Pillow 13.0.0. The newer Streamlit version is necessary to support patched Pillow 13 within package constraints. React Aria selectors and AppTest URL expectations were adapted while preserving navigation, language, GP context, data, v1 and recorded probabilities.

Local validation passed: 405 product tests, seven policy counterexamples, 144 portable tests, ten public-verifier counterexamples, 48 Chromium/WebKit control cases and 16 navigation cases. Dependency audits found no known advisories in 34 presentation and five scientific packages. All 300 examined protected scientific files were unchanged. Five exact historical Gitleaks false positives were reviewed and exempted; a repeat scan was clean. This is not proof about private files or unexamined history.

Existing 2FA was verified, without creating new passkeys. No independent backup/restore test was performed. Initial hosted failures remain recorded in the PR. Session selection tests now wait for smooth scrolling to settle before opening the listbox; eight local PT/EN desktop/mobile cases passed, retaining CSV and tyre-provenance assertions. Hosted CI, merge, release and clean-session public verification require their own subsequent receipts. See [controls and limits](../../docs/en/SECURITY.md).

## Sources

- [GitHubSecurityLab/gh-secure, inspected revision](https://github.com/GitHubSecurityLab/gh-secure/tree/a04d1c144f5d1b63a8aa5cd7946e8ceafa709a2a)
- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [Repository rules API](https://docs.github.com/en/rest/repos/rules)
- [PyPA pip-audit](https://github.com/pypa/pip-audit)
- [Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1)
- [Streamlit PyPI metadata](https://pypi.org/pypi/streamlit/1.66.1/json)
- [Pillow PyPI metadata](https://pypi.org/pypi/pillow/13.0.0/json)
