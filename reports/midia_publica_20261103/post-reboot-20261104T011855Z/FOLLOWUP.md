# Confirmação do uso normal / Normal-browser confirmation

Created by: MBPaschoal
Status: hosting logs requested; root cause open
Type: diagnostic follow-up

## Português

O proprietário confirmou que as bandeiras e o menu inferior também ficam incompletos ou travam no navegador dele. [Resposta preservada](owner-controls-confirmation.json). A falha não se limita às observações automatizadas, mas a causa permanece desconhecida.

Foi solicitado que copie as linhas de erro do painel **Manage app**, que abre os logs conforme a [documentação oficial do Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app). O agente dispõe apenas de acesso público, sem a sessão administrativa. Não foi solicitado outro reboot.

Uma sondagem adicional tentou capturar o corpo de respostas 500 por até 70 segundos após a navegação. Não observou novas respostas nativas com erro nessa abertura; não executou o aceite de controles, fotos e build e não comprova recuperação. [Resultado da sondagem](transport-errors/response-bodies.json), [script](transport-error-probe.cjs). As falhas da rodada completa e seus recibos permanecem inalterados. [Integridade deste complemento](followup-result.json).

## English

The owner confirmed that language flags and bottom navigation also remain incomplete or freeze in their normal browser. [Preserved answer](owner-controls-confirmation.json). The symptom extends beyond automated observations, without establishing root cause.

They were asked to copy error lines from **Manage app**, which opens hosting logs as described in [official Streamlit documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app). The agent has public access only, without an administrative session. No further reboot was requested.

An additional probe tried to capture native 500-response bodies for up to 70 seconds after navigation. It observed no new native error response in that opening; it did not run controls/photo/build acceptance and does not prove recovery. [Probe result](transport-errors/response-bodies.json), [script](transport-error-probe.cjs). Earlier full acceptance failures and receipts remain unchanged. [Follow-up integrity](followup-result.json).
