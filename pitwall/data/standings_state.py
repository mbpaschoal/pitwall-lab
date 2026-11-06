"""Pure presentation state for local standings; never acquires or rewrites data."""

from copy import deepcopy
from datetime import datetime, timezone

FIELDS = ("driver_standings", "constructor_standings")
MESSAGES = {
    "not_captured": "Não há snapshot local do campeonato para esta rodada.",
    "pending": "Ainda aguardamos a classificação desta rodada na fonte consultada.",
    "source_failure": "Não foi possível obter a classificação da fonte na consulta registrada.",
    "incomplete": "Os dados desta consulta estão incompletos; não há uma classificação completa validada.",
    "incompatible": "Esta captura pertence a outro evento e não pode representar o GP selecionado.",
    "cached": "Mostrando o snapshot registrado desta rodada. A atualização mais recente não foi concluída.",
}


def _status(snapshot, identity, envelope=False):
    if not isinstance(snapshot, dict):
        return "incomplete" if snapshot is not None else "not_captured"
    for key, expected in identity.items():
        field = "rodada_referencia" if key == "rodada" else key
        # Operational snapshots inherit season/circuit only from a checked envelope.
        required = key == "rodada" or not envelope
        if field in snapshot and (type(snapshot[field]) is not type(expected) or snapshot[field] != expected):
            return "incompatible"
        if snapshot.get("disponivel") is True and required and field not in snapshot:
            return "incomplete"
    if snapshot.get("disponivel") is True:
        rows = snapshot.get("classificacao")
        return "published" if isinstance(rows, list) and rows and all(isinstance(r, dict) for r in rows) else "incomplete"
    reason = snapshot.get("motivo", "")
    if reason == "evento_incompativel":
        return "incompatible"
    if reason == "rodada_ainda_nao_publicada":
        return "pending"
    if reason == "fonte_indisponivel":
        return "source_failure"
    if reason == "Classificação oficial desta rodada indisponível no snapshot local.":
        return "not_captured"
    return "incomplete"


def admit_weekend_standings(state):
    """Quarantine inconsistent standings in a copy; keep other weekend data."""
    result = deepcopy(state)
    identity = {k: state[k] for k in ("temporada", "rodada", "circuito_id")}
    standings = result.get("campeonatos")
    if standings is None:
        return result
    if not isinstance(standings, dict):
        result["campeonatos"] = {f: dict(disponivel=False, motivo="dados_incompletos") for f in FIELDS}
        return result
    for field in FIELDS:
        if field not in standings:
            continue
        status = _status(standings[field], identity, envelope=True)
        if status in ("incompatible", "incomplete"):
            standings[field] = dict(disponivel=False, classificacao=[],
                                    motivo="evento_incompativel" if status == "incompatible" else "dados_incompletos")
    return result


def resolve_standings(panels, weekend=None):
    """Select exact-event snapshots, preserving a valid fallback and refresh state.

    Inputs already passed their respective row/schema readers. Explicit identity
    mismatches are still rejected here, including persisted operational projections.
    Unknown provider errors stay validation failures, never publication claims.
    """
    result = deepcopy(panels)
    identity = {k: panels[k] for k in ("temporada", "rodada", "circuito_id")}
    operational = weekend.get("campeonatos", {}) if isinstance(weekend, dict) else {}
    envelope_valid = isinstance(weekend, dict) and all(
        type(weekend.get(k)) is type(v) and weekend.get(k) == v for k, v in identity.items()
    )
    for field in FIELDS:
        base = panels.get(field)
        base_status = _status(base, identity)
        candidate = operational.get(field) if isinstance(operational, dict) else None
        status = base_status
        if (base_status == "published" and base.get("estado_publicacao") == "cached"
                and base.get("estado_consulta") in ("pending", "source_failure", "incomplete", "incompatible")):
            status = "cached"
        chosen = base
        refresh = None
        if candidate is not None:
            status = _status(candidate, identity, envelope=True) if envelope_valid else "incompatible"
            if status == "published":
                chosen = candidate
            elif base_status == "published":
                chosen, refresh, status = base, status, "cached"
            else:
                chosen = candidate
        snapshot = deepcopy(chosen) if isinstance(chosen, dict) else {}
        snapshot["estado_publicacao"] = status
        if status in ("published", "cached"):
            snapshot.update(temporada=identity["temporada"], circuito_id=identity["circuito_id"])
        if refresh:
            snapshot["estado_consulta"] = refresh
        if status not in ("published", "cached"):
            snapshot.update(disponivel=False, classificacao=[])
        result[field] = snapshot
    return result


def publication_message(snapshot):
    return MESSAGES.get(snapshot.get("estado_publicacao") or _status(snapshot, {}), "")


def capture_utc(snapshot):
    """Only a timezone-aware timestamp in the snapshot can identify its capture."""
    value = snapshot.get("obtido_em_utc")
    try:
        instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if instant.tzinfo is not None:
            return instant.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (AttributeError, TypeError, ValueError):
        pass
    return None
