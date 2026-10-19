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

O exportador valida uma allowlist contra o commit base da etapa 6, recusa fontes
alteradas, symlinks e destinos não vazios diferentes. O manifesto do pacote
registra o commit e hashes de origem/destino. Não use `git add -A` no cofre para
preparar uma publicação: a seleção deve começar pela lista
`ARQUIVOS_PUBLICACAO.txt` do pacote gerado.
