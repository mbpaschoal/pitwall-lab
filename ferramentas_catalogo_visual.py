"""Baixa e registra ativos de circuito com metadados verificados na Wikimedia.

Uso manual e reprodutível. Este script não consulta dados esportivos, não executa
inferência e não altera artefatos científicos. Fotos usam miniaturas de 1600 px;
mapas vetoriais são preservados no formato original quando possível.
"""
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API = 'https://commons.wikimedia.org/w/api.php'
UA = 'PitwallLab/catalogo-visual (educational portfolio; sequential asset client)'
ESPERADAS = ('CC0', 'CC BY', 'CC BY-SA')


CANDIDATOS = {
    'albert_park': ('Albert Park circuit main straight, pictured from above teams\' garages in 2022.jpg', '2022 F1 CourseLayout Australia.svg'),
    'americas': ('Circuit of the Americas, Austin, TX (30066328424).jpg', '2022 F1 CourseLayout COTA.svg'),
    'bahrain': ('Bahrain International Circuit before the F1 race - 2024.jpg', 'Bahrain International Circuit--Grand Prix Layout with DRS.svg'),
    'baku': ('Baku City Circuit, April 9, 2018 SkySat.jpg', 'Formula1 Circuit Baku.svg'),
    'catalunya': ('Circuit de Catalunya Formula One.jpg', 'Formula1 Circuit Catalunya.svg'),
    'hungaroring': ('Hungaroring 2020.jpg', '2022 F1 CourseLayout Hungary.svg'),
    'imola': ('WTCC08 Dino ed Enzo Ferrari Circuit Imola.jpg', 'Autodromo Enzo e Dino Ferrari 2022.png'),
    'interlagos': ('Interlagos 2006 aerial.jpg', '2014 Interlagos circuit map.svg'),
    'jeddah': ('Jeddah Corniche Circuit viewed from above.png', '2023 F1 CourseLayout Saudi-Arabia.svg'),
    'losail': ('Grand Stand.JPG', 'Lusail International Circuit 2023.svg'),
    'madring': ('Circuito MADRING Sur.jpg', 'Madring Formula 1 Circuit.svg'),
    'marina_bay': ('Singapore (SG), Marina Bay Street Circuit, F1 Pit Building -- 2019 -- 4478.jpg', 'Marina Bay circuit 2023.svg'),
    'miami': ('Start of the Porsche Sprint Challenge North America at the F1 Miami GP - 2022.jpg', '2022 F1 CourseLayout Miami.svg'),
    'monaco': ('Race track circuit de monaco.jpg', 'Monte Carlo Formula 1 track map with streets.svg'),
    'monza': ('Circuito de Monza08.jpg', 'Monza Map-2021.png'),
    'red_bull_ring': ('Luftaufnahme (c)Red Bull Ring.jpg', 'Circuit Red Bull Ring.svg'),
    'rodriguez': ('Autódromo Hermanos Rodríguez, June 4, 2018 SkySat (cropped).jpg', 'Autodromo Hermanos Rodriguez (National Circuit with Foro Sol).png'),
    'sepang': ('Sepang International Circuit.JPG', 'Sepang.svg'),
    'shanghai': ('Shanghai International Circuit, April 7, 2018 SkySat.jpg', 'Shanghai International Racing Circuit track map.svg'),
    'silverstone': ('Silverstone Racing Circuit.jpg', '2022 F1 CourseLayout Britain.svg'),
    'spa': ('Spa-Francorchamps overview.jpg', 'Spa Francorchamps 2022.png'),
    'suzuka': ('Suzukacircuit main-straight.jpg', 'Suzuka circuit map--2005.svg'),
    'vegas': ('2024 Las Vegas Grand Prix at the Sphere - Friday, November 22, Orbi.jpg', 'Las Vegas Strip Circuit 2023.png'),
    'villeneuve': ('Circuit Gilles Villeneuve, Montreal.jpg', '2022 F1 CourseLayout Canada.svg'),
    'yas_marina': ('YasMarina2.jpeg', '2022 F1 CourseLayout Abu Dhabi.svg'),
    'zandvoort': ('Circuit Zandvoort motorsport race track in the Netherlands (46940292845).jpg', '2022 F1 CourseLayout Netherlands.svg'),
}


def _texto(valor):
    if isinstance(valor, dict):
        return str(valor.get('value', '')).strip()
    return str(valor or '').strip()


def _api(titulo, miniatura):
    params = {
        'action': 'query', 'format': 'json', 'formatversion': 2,
        'prop': 'imageinfo', 'titles': 'File:' + titulo,
        'iiprop': 'url|mime|size|extmetadata',
        'iiurlwidth': miniatura,
    }
    req = Request(API + '?' + urlencode(params), headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urlopen(req, timeout=45) as resposta:
        dados = json.loads(resposta.read().decode('utf-8'))
    paginas = dados.get('query', {}).get('pages', [])
    if len(paginas) != 1 or paginas[0].get('missing') or not paginas[0].get('imageinfo'):
        raise ValueError('Arquivo Wikimedia não encontrado: {}'.format(titulo))
    info = paginas[0]['imageinfo'][0]
    meta = info.get('extmetadata', {})
    licenca = _texto(meta.get('LicenseShortName'))
    if not any(licenca.startswith(item) for item in ESPERADAS):
        raise ValueError('Licença não admitida para {}: {}'.format(titulo, licenca or 'ausente'))
    return {
        'titulo': paginas[0].get('title', 'File:' + titulo).removeprefix('File:'),
        'pagina': 'https://commons.wikimedia.org/wiki/' + paginas[0].get('title', 'File:' + titulo).replace(' ', '_'),
        'autor': _texto(meta.get('Artist')),
        'licenca': licenca,
        'url_licenca': _texto(meta.get('LicenseUrl')),
        'credito': _texto(meta.get('Credit')),
        'mime': info.get('mime'),
        'url_original': info.get('url'),
        'url_otimizada': info.get('thumburl') or info.get('url'),
    }


def _baixar(url, destino):
    req = Request(url, headers={'User-Agent': UA})
    with urlopen(req, timeout=90) as resposta:
        bruto = resposta.read()
    if not bruto:
        raise ValueError('Download vazio: {}'.format(url))
    destino.write_bytes(bruto)
    return hashlib.sha256(bruto).hexdigest()


def gerar(raiz, pausa=1.0):
    raiz = Path(raiz)
    pasta = raiz / 'dashboard_assets' / 'circuit'
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / 'catalogo_visual.json'
    try:
        catalogo = json.loads(destino.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        catalogo = {'versao': 1, 'fonte': 'Wikimedia Commons API', 'circuitos': {}}
    if catalogo.get('versao') != 1 or not isinstance(catalogo.get('circuitos'), dict):
        raise ValueError('Catálogo visual local inválido; não sobrescreva sem revisão.')
    for indice, (circuito, (foto_titulo, mapa_titulo)) in enumerate(sorted(CANDIDATOS.items()), start=1):
        existente = catalogo['circuitos'].get(circuito)
        if isinstance(existente, dict):
            caminhos = [raiz / existente.get(tipo, {}).get('caminho', '') for tipo in ('foto', 'mapa')]
            if all(caminho.is_file() and caminho.stat().st_size > 0 for caminho in caminhos):
                print('{:02d}/{} {} (retomado)'.format(indice, len(CANDIDATOS), circuito), flush=True)
                continue
        foto = _api(foto_titulo, 1600)
        time.sleep(pausa)
        mapa = _api(mapa_titulo, 1600)
        time.sleep(pausa)
        foto_ext = '.jpg' if foto['mime'] == 'image/jpeg' else '.png'
        mapa_ext = '.svg' if mapa['mime'] == 'image/svg+xml' else '.png'
        foto_path = pasta / '{}-hero{}'.format(circuito, foto_ext)
        mapa_path = pasta / '{}-layout{}'.format(circuito, mapa_ext)
        foto['caminho'] = str(foto_path.relative_to(raiz))
        mapa['caminho'] = str(mapa_path.relative_to(raiz))
        foto['sha256'] = _baixar(foto['url_otimizada'], foto_path)
        time.sleep(pausa)
        mapa['sha256'] = _baixar(mapa['url_original'], mapa_path)
        time.sleep(pausa)
        catalogo['circuitos'][circuito] = {
            'foto': foto,
            'mapa': mapa,
            'alt_foto': 'Fotografia ilustrativa do circuito {}.'.format(circuito.replace('_', ' ')),
            'alteracoes': 'Foto redimensionada pela miniatura da Wikimedia; mapa preservado no arquivo publicado pela fonte.',
        }
        destino.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print('{:02d}/{} {}'.format(indice, len(CANDIDATOS), circuito), flush=True)
    return catalogo


if __name__ == '__main__':
    gerar(Path(__file__).resolve().parent)
