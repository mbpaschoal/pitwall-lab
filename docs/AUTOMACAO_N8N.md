# Supervisão gratuita com n8n Community

Created by: MBPaschoal
Status: implemented; local execution and hosted publication are separate
Type: operational documentation

[English](en/N8N_AUTOMATION.md) · [P1 hospedado](AUTOMACAO_P1.md)

## O que funciona

O workflow versionado em [automation/n8n/supervisor.json](../automation/n8n/supervisor.json) agenda uma consulta nos minutos 17 e 47, no fuso `America/Sao_Paulo`. O n8n Community local chama uma ponte Python restrita a `127.0.0.1:5681`. A ponte lê APIs públicas e arquivos publicados; não usa tokens, credenciais do Codex, modelos de linguagem pagos nem conexão adicional ao Dropbox. O executor científico permanece no GitHub Actions.

As cinco funções gratuitas são: monitorar estados, organizar pendências, gerar resumos PT/EN, arquivar evidências pequenas com SHA-256 na pasta Dropbox já sincronizada e detectar alterações em documentos oficiais. Os avisos são notificações do próprio Mac, apenas em mudanças relevantes. A fila e os relatórios persistem mesmo que as notificações estejam bloqueadas pelo sistema. Não envia e-mails, Slack ou mensagens a terceiros.

Consulta a última execução concluída de coleta e de produto em `main`; um resultado diferente de sucesso ou coleta sem conclusão recente entra na fila. Sucesso do workflow não prova término observado de Q, existência do par ou aceite do host. Erros HTTP, limitação de API, arquivos incompletos e falhas de validação ficam indeterminados e exigem revisão.

O monitor admite somente `2026/20/interlagos`, com a largada revisada de 08/11 às 17h UTC. Confere os recibos públicos com os validadores P1 originais fixados por hash, identidade, digest, tamanho e horários; o aceite do host permanece separado. É uma auditoria dos recibos publicados, sem refazer a validação nativa das entradas ou observar novamente o site. Nenhuma escrita no GitHub, coleta científica, inferência, ajuste ou promoção de modelo é disparada.

Após aparecerem recibos posteriores válidos, produz resumos dos Brier/log loss fixados, conferindo novamente o cálculo e os denominadores. Alvos desconhecidos permanecem desconhecidos. Não substitui a análise formal dos 20 GPs. Antes desse resultado, o relatório informa espera e não inventa métricas.

## Arquivos e retenção

- `reports/supervisao_n8n/latest.pt.md` e `latest.en.md`: estado legível mais recente.
- `reports/supervisao_n8n/queue.json`: fila de revisão; alterações oficiais ficam abertas para revisão humana.
- `reports/supervisao_n8n/objects/`: bytes originais identificados por SHA-256, conferidos após a gravação.
- `reports/supervisao_n8n/runs/` e `summaries/`: recibos e resumos imutáveis; arquivos `latest` são apenas ponteiros de conveniência.

O arquivamento inicial cobre os JSONs públicos de operação, metadados e pequenos recibos P1, a página oficial do calendário de São Paulo e o PDF FIA do resultado final do México já usado pelo projeto. Não baixa todos os ZIPs de releases. Documentos oficiais são consultados no máximo uma vez a cada 24 horas; alterações de texto/links visíveis ou bytes do PDF geram revisão, sem alterar calendário, fontes admitidas ou previsões. O HTML bruto é preservado, mas scripts dinâmicos não disparam revisão por si só.

São consultas limitadas, seriais, com timeout de 30 s e limite de 4 MiB por resposta. O estado local usa lock e cooldown de 20 minutos, inclusive após reinício. Assets válidos em cache são reutilizados pelos mesmos hashes; 403/429 não viram ausência. A cópia no Dropbox usa a sincronização existente; sua confirmação local não comprova upload concluído nem constitui backup independente.

## Instalação local e manutenção

Runtime, banco, configuração e chaves internas ficam em `~/Library/Application Support/Pitwall Lab/n8n/`, fora do Dropbox e do Git. A implantação copia apenas os módulos necessários e o protocolo congelado, evitando depender de checkout temporário ou placeholders. n8n 2.46.6 e dependências ficam fixados no lockfile; o Node 24 e o Python 3.12 existentes são reutilizados. Não altera o ambiente científico. O n8n não recebe tokens herdados, pacotes Community adicionais, telemetria ou execução de shell habilitada.

No checkout íntegro, com o Python existente:

```bash
python3 automation/n8n/local.py install
python3 automation/n8n/local.py deploy
python3 automation/n8n/local.py agents
python3 automation/n8n/local.py execute
```

`install` é uma ação explícita de instalação; a rotina não instala nem atualiza pacotes sozinha. Para atualizar o supervisor, pare seus serviços com `stop`, revise/teste as alterações, execute `deploy` e inicie novamente com `agents`. `export` salva apenas o JSON do workflow, sem exportar credenciais. Os dois LaunchAgents com prefixo `com.mbpaschoal.pitwall.n8n.` iniciam no login e reiniciam após falha. Logs locais ficam na subpasta `logs/`; a auditoria durável está no Dropbox. Saída de execução CLI é reduzida a um recibo sem tokens internos.

O editor fica em <http://localhost:5678>. A criação da conta proprietária na interface, se solicitada, é local e gratuita; não é conta do serviço Cloud e não é necessária para o agendamento já publicado por CLI. A agenda local depende de Mac ligado, sessão disponível e rede; não garante pontualidade. A operação P1 hospedada continua independente. A conta Cloud, servidor pago, alertas por canais externos e conexão de escrita ao Dropbox ficam fora desta implantação.

## Verificação

`python3 -B -m unittest tests.test_supervision tests.test_prospective_automation tests.test_releases -v` cobre ausência, erros de fonte, deduplicação, recuperação, fronteira temporal, desconhecidos e preservação. Uma execução real via n8n deve gerar evidência em `reports/supervisao_n8n/`; repetir antes do cooldown precisa retornar `cooldown`, sem nova consulta. Instalação, execução CLI, agendamento observado e futura avaliação pós-GP têm recibos separados.

Referências: [instalação](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-npm.md), [CLI](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line.md), [Community](https://docs.n8n.io/deploy/host-n8n/community-edition-features.md).
