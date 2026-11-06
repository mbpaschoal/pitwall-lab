"""Reuse the validated archive projection while all four input contents match."""
from hashlib import sha256
from pathlib import Path

from streamlit import cache_data

from pitwall.data import archive, complementary_sources, identity_revision, tyre_age


_INPUTS = (
    (archive.ASSET, archive.MAX_BYTES, True),
    (tyre_age.ASSET, tyre_age.MAX_BYTES, False),
    (complementary_sources.ASSET, 512 * 1024, False),
    (identity_revision.ASSET, 64 * 1024, False),
)


def _content_signature(root):
    """Check paths on every call; timestamps never establish content identity."""
    signatures = []
    try:
        for relative, limit, required in _INPUTS:
            path = root / relative
            current = path
            while current != root:
                if current.is_symlink():
                    raise archive.AcervoDashboardErro("O acervo não pode usar symlink.")
                current = current.parent
            if not path.exists() and not required:
                signatures.append(None)
                continue
            if not path.is_file() or path.stat().st_size > limit:
                raise archive.AcervoDashboardErro("Entrada do acervo ausente ou inválida: {}".format(relative))
            raw = path.read_bytes()
            if len(raw) > limit:
                raise archive.AcervoDashboardErro("Entrada do acervo excede o limite: {}".format(relative))
            signatures.append(sha256(raw).hexdigest())
    except OSError as error:
        raise archive.AcervoDashboardErro("Não foi possível ler as entradas do acervo: {}".format(error)) from error
    return tuple(signatures)


@cache_data(show_spinner=False, max_entries=4)
def _load_cached(root, signatures):
    # Keep the canonical loader and all its validations/complement guards.
    result = archive.carregar(root)
    if _content_signature(Path(root)) != signatures:
        raise archive.AcervoDashboardErro("As entradas do acervo mudaram durante a leitura; tente novamente.")
    return result


def carregar(raiz):
    """Return an isolated copy; changed, removed or unsafe inputs miss the cache."""
    root = Path(raiz).resolve()
    return _load_cached(str(root), _content_signature(root))
