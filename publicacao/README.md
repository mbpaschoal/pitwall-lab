# Fontes da etapa 7 — distribuição pública mínima

Created by: MBPaschoal
Status: recipe source
Type: publication templates

Esta pasta contém somente a receita e os modelos de texto usados por
`exportar_dashboard.py`. Ela não é copiada integralmente para a distribuição.

Na raiz do projeto, gere o pacote padrão com:

```bash
./.venv/bin/python exportar_dashboard.py
```

Para uma pasta nova fora do cofre:

```bash
./.venv/bin/python exportar_dashboard.py --destino "/caminho/novo/pitwall-dashboard"
```

A receita v2 separa proveniências: os nove CSV/JSON científicos são conferidos
byte a byte contra o commit-base congelado `05eec0b70b24abf9a68dae45aac36730eefb5bc5`;
a interface Race Weekend, o adaptador 2026, o asset local e as fontes OFL são
registrados como `UNCOMMITTED` com hashes atuais do working tree. Ela recusa
symlinks, segredos, cache, caminhos com `..` e destinos não vazios divergentes.
O ZIP determinístico acompanha o pacote. Não use `git add -A` no cofre: a seleção
futura deve começar em `ARQUIVOS_PUBLICACAO.txt`.
