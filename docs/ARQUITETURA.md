# Organização do código

Português · [English](en/ARCHITECTURE.md)

O [blueprint](BLUEPRINT.md) determina responsabilidades. A implementação usa um pacote Python importável, sem instalação adicional. `app.py` continua sendo o entrypoint do Streamlit; módulos pequenos na raiz encaminham os comandos antigos.

| Área | Implementação | Responsabilidade |
|---|---|---|
| Dashboard | `pitwall/dashboard/` | Composição, navegação e vistas do acervo. |
| Dados | `pitwall/data/` | Leitores, validação, projeção offline, aquisição serial e adjudicação. |
| Idiomas | `pitwall/i18n/` | Catálogo offline PT/EN e adaptação exclusiva de apresentação. |
| Pesquisa | `pitwall/research/` | Pesquisa retrospectiva v2 isolada, sem promoção do modelo. |
| Operação | `operacao2026/` | Snapshots, corte, estado e emissão de GPs. |
| Publicação | `pitwall/publishing/`, `publicacao/`, `exportar_dashboard.py` | Documentação allowlistada, templates e exportação portátil. |
| Revisão | `tests/`, `validar_blueprint.py`, `verificar_pacote.py` | Contratos, regressões, integridade e aceite no navegador. |
| Evidência científica | `data/`, `models/`, `reports/`, produtores v1 originais | Artefatos e scripts congelados, preservados nos caminhos originais. |

## Fluxo e limites

A aquisição é explícita e serial. A preparação offline gera assets. Leitores verificam schemas e identidades. A interface apresenta cópias locais; não coleta, treina ou infere durante a navegação. O exportador usa allowlist e distingue baseline científico de build de apresentação.

Os módulos da raiz com nome antigo existem para compatibilidade; não são implementações duplicadas. Novas mudanças devem ocorrer no pacote. A compatibilidade preserva imports usados pelos testes e por comandos existentes. Os scripts v1 congelados não foram movidos só para uniformizar a aparência das pastas: seus caminhos e hashes são parte da evidência.

## Tradução

`pitwall/i18n/en.json` contém os textos visíveis. Português é o padrão. O idioma é específico da sessão e persiste como `lang=pt|en` nos links. Valores canônicos de widgets, IDs, caminhos e URLs não são traduzidos. A camada `streamlit.py` adapta apenas argumentos de exibição e cópias de tabelas/gráficos; o Streamlit não recebe patches globais.

Documentos ingleses ficam em `docs/en/`; a seleção usa uma allowlist explícita. Downloads científicos conservam os bytes e identificadores originais, acompanhados de explicação em inglês. Downloads de tabelas descritivas seguem o idioma selecionado. Uma tradução nunca altera os dados-fonte nem a evidência de disponibilidade temporal.

## Como alterar

Comece pelo contrato de papel no blueprint. Mantenha funções pequenas, nomes descritivos, dependências explícitas e testes no comportamento. Evite copiar implementações entre pacote, raiz e distribuição: o pacote portátil é gerado. Registre nova versão para cada entrega e teste o pacote isolado e o idioma afetado. Não faça descoberta irrestrita de testes para uma alteração de apresentação: ela pode executar ciência.
