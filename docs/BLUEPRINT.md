# Responsabilidades do blueprint / Blueprint responsibilities

## Português

O blueprint organiza o trabalho por contrato. Ele não executa coleta, treino, emissão ou publicação automaticamente. A implementação do produto segue os papéis abaixo; os contratos locais detalhados ficam em `skills/pitwall-lab/`, dentro do ambiente de autoria. O cofre e os repositórios de referência não são copiados para a distribuição pública.

| Papel | Código e responsabilidade |
|---|---|
| Dados | `pitwall/data/`: identidade, schemas, cache serial, ausências, fontes e projeção offline. |
| Metodologia | `pitwall/research/`: pesquisa v2 retrospectiva; v1 e seus artefatos continuam congelados. |
| Operação | `operacao2026/`: snapshots, corte, estado e emissões registradas por GP. |
| Dashboard | `pitwall/dashboard/`, `pitwall/i18n/`: apresentação, interação e idiomas sem executar ciência. |
| Distribuição | `pitwall/publishing/`, `publicacao/`, `exportar_dashboard.py`: allowlist, manifesto e pacote isolado. |
| Cofre | Conhecimento local em `notes/`, `ideas/`, `inbox/`; fora da distribuição pública. |
| Documentação | README, `docs/`, versões e aprendizado sustentados por evidências. |
| Revisão | Testes focais, preservação de hashes e aceite real em desktop/mobile. |

A ordem das dependências é dados → projeção → apresentação → pacote → verificação pública. Documentação acompanha o comportamento implementado. Cada nova entrega de dados/melhoria precisa de versão e notas PT/EN. Não criar métricas ou preencher ausências para aparentar conclusão; não alterar a probabilidade congelada com dados posteriores.

Os scripts v1 originais são uma exceção explícita à migração física: preservam caminhos e hashes. Os demais módulos antigos da raiz encaminham para o pacote para manter compatibilidade. Consulte a [arquitetura](ARQUITETURA.md) e a [política de versões](VERSOES.md).

## English

The blueprint organises work by contract. It does not automatically execute acquisition, training, recorded predictions or publication. Product implementation follows the roles below; detailed local contracts live in `skills/pitwall-lab/` in the authoring environment. The knowledge vault and reference repositories are not copied into the public distribution.

| Role | Code and responsibility |
|---|---|
| Data | `pitwall/data/`: identity, schemas, serial cache, missingness, sources and offline projection. |
| Methodology | `pitwall/research/`: retrospective v2 research; v1 and its artefacts remain frozen. |
| Operations | `operacao2026/`: snapshots, cutoff, state and per-GP recorded predictions. |
| Dashboard | `pitwall/dashboard/`, `pitwall/i18n/`: presentation, interaction and languages without scientific execution. |
| Distribution | `pitwall/publishing/`, `publicacao/`, `exportar_dashboard.py`: allowlist, manifest and isolated package. |
| Knowledge vault | Local `notes/`, `ideas/`, `inbox/`; outside the public distribution. |
| Documentation | Evidence-based README, `docs/`, versions and learning journal. |
| Review | Focused tests, hash preservation and actual desktop/mobile acceptance. |

Dependency order is data → projection → presentation → package → public verification. Documentation follows implemented behaviour. Every new data/improvement delivery needs a version and PT/EN notes. Do not invent metrics or fill missing values to suggest completion; do not change frozen probabilities using later data.

Original v1 scripts are an explicit physical-migration exception: retain paths/hashes. Other old root modules forward to the package for compatibility. See [architecture](en/ARCHITECTURE.md) and [version policy](en/VERSIONS.md).

## Referência / Reference

Adapted from [devton/agentic-workflow-blueprint](https://github.com/devton/agentic-workflow-blueprint), with project-specific temporal and evidence boundaries. A routing contract is not an installed global command or an authorisation to run unrelated workflows.
