"""Valida inventário/build e executa somente testes portáteis, no CWD do pacote."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from exportar_dashboard import COMMIT_BASE_PADRAO

TESTES_PORTATEIS = ('test_distribuicao.py', 'test_acervo_publico.py',
                    'test_dashboard_app.py', 'test_dashboard_dados.py', 'test_interface_editorial.py',
                    'test_driver_conditions.py', 'test_driver_projection.py', 'test_pilot_views.py',
                    'test_fan_exploration.py', 'test_review_regressions.py')


def validar_pacote(pacote):
    pacote = Path(pacote).resolve()
    projeto = Path(__file__).resolve().parent
    if pacote == projeto or not (pacote / 'MANIFESTO.json').is_file():
        raise ValueError('Escolha um pacote exportado, nunca a raiz científica como CWD de testes portáteis.')
    m = json.loads((pacote / 'MANIFESTO.json').read_text())
    if m.get('baseline_cientifico_commit') != COMMIT_BASE_PADRAO or m.get('commit_origem') != COMMIT_BASE_PADRAO:
        raise ValueError('Baseline científico divergente')
    versao = (pacote / 'VERSION').read_text().strip()
    if not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', versao) or m.get('versao_produto') != versao:
        raise ValueError('Versão do produto diverge do manifesto')
    nomes = (pacote / 'ARQUIVOS_PUBLICACAO.txt').read_text().splitlines()
    declarados = [x['caminho'] for x in m['arquivos']]
    if len(nomes) != len(set(nomes)) or len(declarados) != len(set(declarados)) or set(nomes) != set(declarados) | {'MANIFESTO.json'}:
        raise ValueError('Inventário/manifesto divergentes ou duplicados')
    reais = set()
    for pasta, diretorios, arquivos in os.walk(pacote):
        diretorios[:] = [d for d in diretorios if d not in {'.git', '.venv', '__pycache__', '.pytest_cache'}]
        for arquivo in arquivos:
            reais.add((Path(pasta) / arquivo).relative_to(pacote).as_posix())
    if reais != set(nomes):
        raise ValueError('Árvore real diverge do inventário')
    for x in m['arquivos']:
        p = Path(x['caminho'])
        caminho = pacote / p
        if p.is_absolute() or '..' in p.parts or not caminho.resolve().is_relative_to(pacote):
            raise ValueError('Arquivo fora do pacote')
        if any(a.is_symlink() for a in [caminho, *caminho.parents] if a != pacote.parent):
            raise ValueError('Symlink no pacote')
        if hashlib.sha256(caminho.read_bytes()).hexdigest() != x['sha256_destino']:
            raise ValueError('Hash divergente: ' + str(p))
    build = hashlib.sha256(json.dumps([(x['caminho'], x['sha256_destino']) for x in sorted(m['arquivos'], key=lambda x: x['caminho'])],
                                     separators=(',', ':'), ensure_ascii=False).encode('utf8')).hexdigest()
    if build != m['apresentacao_build_sha256']:
        raise ValueError('Build da apresentação divergente')
    if any((pacote / d).exists() for d in ['data', 'models', 'notes', 'projects']):
        raise ValueError('Pacote contém camada não publicável')
    return pacote, m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pacote', required=True, type=Path)
    p.add_argument('--somente-integridade', action='store_true')
    a = p.parse_args()
    pacote, m = validar_pacote(a.pacote)
    print(json.dumps({'cwd': str(pacote), 'build': m['apresentacao_build_sha256'],
                      'testes': [] if a.somente_integridade else TESTES_PORTATEIS}), flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    if not a.somente_integridade:
        for teste in TESTES_PORTATEIS:
            if not (pacote / 'tests' / teste).is_file():
                raise ValueError('Teste portátil ausente: ' + teste)
            subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-p', teste],
                           cwd=pacote, env=env, check=True)


if __name__ == '__main__':
    main()
