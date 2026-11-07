"""Curated names and local motifs for the editorial gouache collection."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Destination:
    name: tuple[str, str]
    country: tuple[str, str]
    motif: tuple[str, str]
    reference: str


DESTINATIONS = {
    'miami': Destination(
        name=('Miami', 'Miami'),
        country=('Estados Unidos', 'United States'),
        motif=('Estádio, palmeiras e cores de Miami', 'Miami stadium, palms and colours'),
        reference='https://tpddesignhouse.com/projects/formula-1-miami-paddock-club/',
    ),
    'suzuka': Destination(
        name=('Suzuka', 'Suzuka'),
        country=('Japão', 'Japan'),
        motif=('Roda-gigante e curvas de Suzuka', 'Suzuka Ferris wheel and bends'),
        reference='https://www.alpinef1.com/news/behind-the-design-japanese-gp-race-poster',
    ),
    'rodriguez': Destination(
        name=('Cidade do México', 'Mexico City'),
        country=('México', 'Mexico'),
        motif=('Arquibancadas do estádio na Cidade do México', 'Mexico City stadium grandstands'),
        reference='https://pinchemoreno.myportfolio.com/ocesa-2015-formula-1-mexican-grand-prix',
    ),
    'interlagos': Destination(
        name=('São Paulo', 'São Paulo'),
        country=('Brasil', 'Brazil'),
        motif=('Curvas, zebras e horizonte de São Paulo', 'Interlagos bends, kerbs and São Paulo skyline'),
        reference='https://autodromodeinterlagos.prefeitura.sp.gov.br/w/nova-identidade-visual-do-autodromo-de-interlagos',
    ),
    'imola': Destination(
        name=('Imola', 'Imola'),
        country=('Itália', 'Italy'),
        motif=('Parque, álamos e curvas de Imola', 'Imola park, poplars and bends'),
        reference='https://www.autodromoimola.it/en/history/',
    ),
    'monaco': Destination(
        name=('Monte Carlo', 'Monte Carlo'),
        country=('Mônaco', 'Monaco'),
        motif=('Porto, iates e fachadas de Monte Carlo', 'Monte Carlo harbour, yachts and facades'),
        reference='https://www.formula1.com/en/racing/2026/monaco',
    ),
    'catalunya': Destination(
        name=('Barcelona', 'Barcelona'),
        country=('Espanha', 'Spain'),
        motif=('Arquibancadas e paisagem mediterrânea da Catalunha', 'Catalan grandstands and Mediterranean landscape'),
        reference='https://www.circuitcat.com/en/',
    ),
    'red_bull_ring': Destination(
        name=('Spielberg', 'Spielberg'),
        country=('Áustria', 'Austria'),
        motif=('Colinas da Estíria e escultura de aço', 'Styrian hills and steel sculpture'),
        reference='https://www.redbullring.com/en/business/',
    ),
    'silverstone': Destination(
        name=('Silverstone', 'Silverstone'),
        country=('Reino Unido', 'United Kingdom'),
        motif=('A cobertura do Wing e o céu de Silverstone', 'The Wing roofline and Silverstone sky'),
        reference='https://populous.com/showcases/silverstone-circuit',
    ),
    'monza': Destination(
        name=('Monza', 'Monza'),
        country=('Itália', 'Italy'),
        motif=('Parque e concreto do oval histórico de Monza', 'Monza park and historic concrete banking'),
        reference='https://www.monzanet.it/en/',
    ),
    'spa': Destination(
        name=('Spa-Francorchamps', 'Spa-Francorchamps'),
        country=('Bélgica', 'Belgium'),
        motif=('A subida de Raidillon na floresta das Ardenas', 'Raidillon climbing through the Ardennes forest'),
        reference='https://www.spa-francorchamps.be/en/the-circuit',
    ),
    'zandvoort': Destination(
        name=('Zandvoort', 'Zandvoort'),
        country=('Países Baixos', 'Netherlands'),
        motif=('Curva inclinada e dunas de Zandvoort', 'Zandvoort banking and coastal dunes'),
        reference='https://www.circuitzandvoort.nl/en/presentation/',
    ),
    'hungaroring': Destination(
        name=('Budapeste', 'Budapest'),
        country=('Hungria', 'Hungary'),
        motif=('Curvas e colinas de Mogyoród', 'Mogyoród bends and hills'),
        reference='https://hungaroring.hu/site/en/media/news/hungaroring-the-future-has-begun',
    ),
    'villeneuve': Destination(
        name=('Montreal', 'Montreal'),
        country=('Canadá', 'Canada'),
        motif=('Parque de Montreal e a Biosphère ao fundo', 'Montreal park and the distant Biosphère'),
        reference='https://www.parcjeandrapeau.com/en/the-dome-biosphere-history/',
    ),
    'bahrain': Destination(
        name=('Sakhir', 'Sakhir'),
        country=('Bahrein', 'Bahrain'),
        motif=('Torre circular de Sakhir e luz do deserto', 'Sakhir circular tower and desert light'),
        reference='https://www.bahraingp.com/blog/news/f1-fans-first-to-witness-bahrains-iconic-bic-tower-in-a-whole-new-light/',
    ),
    'jeddah': Destination(
        name=('Jeddah', 'Jeddah'),
        country=('Arábia Saudita', 'Saudi Arabia'),
        motif=('Corniche, Mar Vermelho e luz de Jeddah', 'Jeddah Corniche, Red Sea and light'),
        reference='https://jeddahcircuit.com/en',
    ),
    'albert_park': Destination(
        name=('Melbourne', 'Melbourne'),
        country=('Austrália', 'Australia'),
        motif=('Lago, eucaliptos e horizonte de Melbourne', 'Albert Park lake, eucalyptus and Melbourne skyline'),
        reference='https://www.formula1.com/en/latest/article/gallery-the-best-images-from-australia.6vjVuD4gMASdZx9sKQqMob',
    ),
    'shanghai': Destination(
        name=('Shanghai', 'Shanghai'),
        country=('China', 'China'),
        motif=('Arquitetura monumental e formas de lótus de Shanghai', 'Shanghai monumental architecture and lotus forms'),
        reference='https://tilke.de/portfolio/shanghai-international-circuit/',
    ),
    'americas': Destination(
        name=('Austin', 'Austin'),
        country=('Estados Unidos', 'United States'),
        motif=('Torre de observação e paisagem do Texas', 'COTA observation tower and Texas landscape'),
        reference='https://www.mirorivera.com/observation-tower',
    ),
    'baku': Destination(
        name=('Baku', 'Baku'),
        country=('Azerbaijão', 'Azerbaijan'),
        motif=('Muralhas e ruas da cidade antiga de Baku', 'Baku old-city walls and streets'),
        reference='https://www.mercedesamgf1.com/news/in-pictures-the-best-images-from-baku',
    ),
    'marina_bay': Destination(
        name=('Marina Bay', 'Marina Bay'),
        country=('Singapura', 'Singapore'),
        motif=('Luzes da pista e arquitetura de Marina Bay', 'Marina Bay track lights and architecture'),
        reference='https://www.astonmartinf1.com/en-GB/news/gallery/the-best-pictures-from-magnificent-marina-bay',
    ),
    'vegas': Destination(
        name=('Las Vegas', 'Las Vegas'),
        country=('Estados Unidos', 'United States'),
        motif=('Esfera, luzes e cenário noturno de Las Vegas', 'Las Vegas sphere, lights and night scene'),
        reference='https://www.mercedesamgf1.com/news/in-pictures-the-best-images-from-las-vegas-2025',
    ),
    'losail': Destination(
        name=('Lusail', 'Lusail'),
        country=('Catar', 'Qatar'),
        motif=('Refletores e pista noturna de Lusail', 'Lusail floodlights and night track'),
        reference='https://www.formula1.com/en/latest/article/speed-desert-and-doha-the-ultimate-fan-guide-to-the-qatar-grand-prix.7pVRowHi0gVBHEROf7d9B0',
    ),
    'yas_marina': Destination(
        name=('Abu Dhabi', 'Abu Dhabi'),
        country=('Emirados Árabes Unidos', 'United Arab Emirates'),
        motif=('Malha iluminada do hotel e marina de Yas', 'Yas hotel illuminated lattice and marina'),
        reference='https://www.marriott.com/en-us/hotels/auhwh-w-abu-dhabi-yas-island/photos/',
    ),
    'madring': Destination(
        name=('Madrid', 'Madrid'),
        country=('Espanha', 'Spain'),
        motif=('Curva inclinada e ambiente de Madrid', 'Madrid banked bend and surroundings'),
        reference='https://www.madring.com/en/circuit',
    ),
    'sepang': Destination(
        name=('Sepang', 'Sepang'),
        country=('Malásia', 'Malaysia'),
        motif=('Coberturas das arquibancadas, palmeiras e pista de Sepang', 'Sepang grandstand canopies, palms and track'),
        reference='https://www.sepangcircuit.com/architecture',
    ),
}
