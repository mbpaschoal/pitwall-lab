# Pitwall Lab

[Português](README.md) · English

[**Open the public dashboard**](https://pitwall-lab.streamlit.app/)

MBPaschoal's Formula 1 data-science portfolio. This package presents individual podium probabilities, evidence and limitations. It does not estimate P1/P2/P3 order or query APIs during navigation.

## Product

- **Drivers:** condition leaders, individual profiles, minimum samples, ties and GP evidence.
- **Races:** circuit, complete standings, times, tyres/stops, weather, teams and up to five previous editions at the same circuit.
- **Predictions:** recorded probabilities and subsequent comparison, separating prospective Austin from retrospective analysis.
- **Performance:** metrics, calibration and explicit coverage.
- **Methodology:** offline documents and reports, also in English.

BR/GB flags in the upper-right corner select the language. Navigation retains season, GP and language. Canonical identifiers and scientific downloads preserve original bytes; descriptive tables follow the selected language.

## Evidence and learning

Frozen model v1: training 2021–2023, already explored 2024 validation and already evaluated 2025. Across the same 22 ranking GPs in 2025, the model identified 51 podium drivers versus qualifying's 50; both identified all three in 8/22 GPs. Probability metrics use 478 cases. This demonstrates neither statistical significance nor future guarantees.

Drivers combines 66 main races and 1,340 starts with sensors within actual racing intervals and edition-specific FIA maps. Eight races recorded rain. The audit records 295 checks; 17 practice/qualifying compounds remain missing and do not enter these rankings. Weather separates race sensors from hourly atmospheric reconstruction. Baku/Q retains its FIA supplement without invented sectors or validity flags.

The History correction showed that an existing table can answer the wrong question. Publication now checks the served build because local tests do not prove deployment. [Evolution and versions](CHANGELOG.en.md).

## Run

Use Python 3.12 in a new environment inside this package:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Implementation is in `pitwall/dashboard`, `pitwall/data` and `pitwall/i18n`; root modules provide compatibility. No joblib models, training, inference or raw data are included. [Hosting](GUIA_HOSPEDAGEM.md), [sources](FONTES_E_DADOS.md), [code licensing](LICENCA_CODIGO.md).

`VERSION` identifies the product independently of model v1 and the build in `MANIFESTO.json`. Each delivered data update or improvement requires a new version and PT/EN notes. Independent educational project without official Formula 1 affiliation.
