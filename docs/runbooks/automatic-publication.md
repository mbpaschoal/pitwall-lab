# Publicação automática com commits concorrentes

Português · English below

A coleta e a publicação têm estados separados. Um commit novo em `main` durante os testes torna antigos a versão, as notas e o pacote preparados na execução. Não se faz merge/rebase desses arquivos gerados e não se usa push forçado.

`operacao2026/publication.py` confere o `main` remoto antes de criar commit/tag. Também trata o intervalo entre essa conferência e o push atômico: só classifica uma rejeição como concorrência quando uma nova consulta comprova que o ramo avançou. Erros de autenticação, transporte ou tag continuam falhas visíveis.

Com avanço comprovado, o fluxo agenda `workflow_dispatch` em `main`, reaproveita o cache de capturas e executa novamente coleta/projeção, incremento a partir da versão atual, exportação e validações. O job anterior registra `retry_scheduled` e não tenta conferir uma versão que não publicou. Há no máximo duas recuperações na mesma cadeia; esgotamento ou falha de agendamento fica explícito, com capturas preservadas para o próximo ciclo regular.

Além do cache limitado a 128 MiB, as capturas são anexadas como artefato da execução antes da tentativa de publicação e permanecem disponíveis por três dias. Uma publicação concluída também inclui o arquivo de capturas na release. Modelo, emissões, protocolos e arquivos científicos não entram na lista de staging.

A permissão `actions: write` serve ao novo disparo do próprio workflow. O GitHub permite que `workflow_dispatch` criado pelo `GITHUB_TOKEN` inicie uma execução; pushes desse token não iniciam outros workflows de push. [Documentação GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [GitHub CLI](https://cli.github.com/manual/gh_workflow_run).

Validação focal, sem APIs de F1: `python -B -m unittest tests.test_automatic_publication`. Os testes usam repositórios Git temporários reais e substituem somente chamadas `gh`, cobrindo avanço anterior e durante o push, versão concorrente, tags preservadas, erro de permissão, limite de tentativas e staging alheio.

## English

Collection and publication have separate outcomes. A concurrent main commit invalidates the prepared version, notes and package. Generated files are never rebased or force-pushed. The publisher checks remote main before commit/tag creation and after an atomic push rejection. Only a proven branch advance triggers recovery; authentication, transport and tag failures remain visible.

Recovery dispatches the same workflow on current main. A fresh checkout restores preserved captures and runs ordinary collection/projection, versioning, export and validation again. The previous job reports `retry_scheduled` and skips deployment verification. A lineage permits at most two recovery runs; exhaustion and dispatch failures remain explicit. Original captures survive in bounded cache and a three-day workflow artifact, and successful releases retain their capture archive.

The `actions: write` permission is used only for self-dispatch. Frozen scientific files, models and original emissions are outside publication staging. Focused tests use real temporary Git repositories and mocked GitHub CLI calls; they exercise both race windows, a concurrent version increment, preserved tags/captures, permission failures, retry limits and unrelated staged work.
