# Comparação controlada da hospedagem / Controlled hosting comparison

Created by: MBPaschoal
Status: proposed; requires owner-authenticated hosting dashboard
Type: diagnostic runbook

O código aprovado está preparado. Esta comparação cria uma segunda instância e preserva o endereço atual. O objetivo é verificar se o mesmo código carrega em outra instância; um resultado positivo isolado não prova a causa do defeito.

The approved code is ready. This comparison creates a second instance and preserves the existing address. It tests whether identical code loads elsewhere; one successful result does not establish root cause.

1. Abra [share.streamlit.io](https://share.streamlit.io), use **Create app** e **Yup, I have an app**.
2. Preencha os campos abaixo. Alternativamente, use **Paste GitHub URL** com [o arquivo da branch aprovada](https://github.com/mbpaschoal/pitwall-lab/blob/codex/navigation-fallback-20261104/distribuicao/pitwall-dashboard/app.py).
3. Em **Advanced settings**, selecione Python **3.12**. Este aplicativo não precisa de secrets para apresentar os artefatos locais.
4. Publique a instância de verificação e envie o novo endereço. O agente executará as mesmas verificações PT/EN desktop/celular; só depois será possível comparar os resultados.

| Campo / Field | Valor / Value |
|---|---|
| Repository | `mbpaschoal/pitwall-lab` |
| Branch | `codex/navigation-fallback-20261104` |
| Main file path | `distribuicao/pitwall-dashboard/app.py` |
| App URL | `pitwall-lab-verificacao`, se disponível / if available |
| Python | `3.12` |

English: open the workspace, choose Create app, fill the fields above, select Python 3.12 in Advanced settings and deploy the comparison instance. Share its URL for the same clean-browser acceptance. This app needs no secrets to display local artifacts.

A necessidade desta ação vem da falta de acesso administrativo autenticado nesta sessão, não de aprovação adicional do código. Não foi criado novo serviço ou encerrada a instância atual pelo agente.

This action is needed because the current session has no authenticated hosting administration access, not because code approval is outstanding. The agent has not created a new service or shut down the current instance.

Fonte primária consultada em 04/11/2026 / Primary source accessed on 4 November 2026: [Streamlit — Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
