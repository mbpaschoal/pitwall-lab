"""Original editorial linework and art direction for each hosted circuit.

These are decorative interpretations of local places. Circuit measurements,
official maps, photographs and prediction inputs keep their separate sources.
"""
from dataclasses import dataclass
from math import cos, pi, sin


@dataclass(frozen=True)
class Destination:
    name: tuple[str, str]
    motif: tuple[str, str]
    palette: tuple[str, str, str, str]  # paper, ink, accent, second ink
    artwork: str
    frame: str = 'diagonal'
    photo_position: str = 'center'
    reference: str = ''


def _suzuka_wheel():
    spokes, cabins = [], []
    for index in range(12):
        angle = index * pi / 6
        x, y = 148 + 94 * cos(angle), 144 + 94 * sin(angle)
        spokes.append('<path d="M148 144L{:.2f} {:.2f}"/>'.format(x, y))
        cabins.append('<rect x="{:.2f}" y="{:.2f}" width="14" height="18" rx="3"/>'.format(x-7, y-5))
    return ('<g fill="none" stroke="var(--pc-accent)" stroke-width="3">'
            '<circle cx="148" cy="144" r="94"/>' + ''.join(spokes) +
            '<path d="M148 144L106 298M148 144L190 298M92 298H206"/></g>'
            '<g fill="var(--pc-paper)" stroke="var(--pc-accent)" stroke-width="3">' + ''.join(cabins) + '</g>'
            '<path d="M14 324C70 272 110 362 158 328S220 270 254 302S194 350 160 318S104 278 74 298" '
            'fill="none" stroke="var(--pc-second)" stroke-width="7"/>')


def _biosphere():
    return '''<defs><clipPath id="pc-biosphere"><path d="M87 244A112 112 0 1 1 209 244Z"/></clipPath></defs>
    <g fill="none" stroke="var(--pc-ink)" stroke-width="2.4">
    <path d="M87 244A112 112 0 1 1 209 244Z"/>
    <g clip-path="url(#pc-biosphere)"><path d="M26 90H270M26 150H270M26 210H270M87 30L26 150L87 270L209 30L270 150L209 270M26 90L209 270M87 30L270 210M209 30L26 210M270 90L87 270"/></g>
    <path d="M98 244V278M198 244V278M76 278H220"/></g>
    <path d="M0 306C84 284 162 324 302 302" fill="none" stroke="var(--pc-accent)" stroke-width="18"/>'''


# Each drawing has its own silhouette; none is a recoloured generic cityscape.
ARTWORKS = {
    'miami': '''<path d="M30 302V112H62V82H96V58H170V82H204V112H236V302" fill="none" stroke="var(--pc-ink)" stroke-width="6"/>
    <path d="M82 282V116M108 282V90M134 282V90M160 282V90M186 282V116" stroke="var(--pc-accent)" stroke-width="9"/>
    <path d="M16 319H264M16 334H264M109 42H157" stroke="var(--pc-second)" stroke-width="5"/>''',
    'suzuka': _suzuka_wheel(),
    'rodriguez': '''<path d="M0 134L144 94L286 134V254L144 314L0 254Z" fill="var(--pc-second)"/>
    <path d="M0 158L144 118L286 158M0 181L144 141L286 181M0 204L144 164L286 204M0 227L144 187L286 227" fill="none" stroke="var(--pc-paper)" stroke-width="4"/>
    <path d="M27 230L144 196L260 230L144 278Z" fill="var(--pc-accent)"/>
    <path d="M-18 336L160 248L302 288" fill="none" stroke="var(--pc-ink)" stroke-width="20"/>
    <path d="M-18 336L160 248L302 288" fill="none" stroke="var(--pc-paper)" stroke-width="3"/>''',
    'interlagos': '''<path d="M-30 348C18 270 142 321 198 254S172 167 106 181S40 121 104 68S239 56 286 14" fill="none" stroke="var(--pc-ink)" stroke-width="49"/>
    <path d="M-30 348C18 270 142 321 198 254S172 167 106 181S40 121 104 68S239 56 286 14" fill="none" stroke="var(--pc-paper)" stroke-width="38"/>
    <path d="M-30 348C18 270 142 321 198 254S172 167 106 181S40 121 104 68S239 56 286 14" fill="none" stroke="var(--pc-accent)" stroke-width="5" stroke-dasharray="15 13"/>
    <path d="M8 342L272 294" stroke="var(--pc-second)" stroke-width="10"/>''',
    'americas': '''<path d="M108 321L118 47H151L176 321M115 70H158M112 102H160M111 136H162M110 171H165M109 208H168M108 248H171M107 286H174" fill="none" stroke="var(--pc-accent)" stroke-width="5"/>
    <path d="M102 48C146 36 191 41 233 60L225 81L107 68ZM151 48L199 322" fill="none" stroke="var(--pc-ink)" stroke-width="5"/>
    <path d="M18 340H278M98 326H209" stroke="var(--pc-second)" stroke-width="9"/>''',
    'bahrain': '''<path d="M91 299V73H196V299" fill="var(--pc-second)"/>
    <g fill="var(--pc-paper)" stroke="var(--pc-ink)" stroke-width="3">
    <ellipse cx="144" cy="76" rx="78" ry="20"/><ellipse cx="144" cy="111" rx="77" ry="20"/><ellipse cx="144" cy="147" rx="76" ry="20"/><ellipse cx="144" cy="183" rx="74" ry="20"/><ellipse cx="144" cy="219" rx="71" ry="20"/><ellipse cx="144" cy="254" rx="67" ry="20"/>
    </g><path d="M22 316H268M40 334H286" stroke="var(--pc-accent)" stroke-width="7"/>''',
    'jeddah': '''<path d="M0 336C92 258 35 185 116 143S220 80 286 0" fill="none" stroke="var(--pc-second)" stroke-width="66"/>
    <path d="M0 336C92 258 35 185 116 143S220 80 286 0" fill="none" stroke="var(--pc-paper)" stroke-width="7"/>
    <path d="M40 278V210L62 184M120 196V129L144 104M200 108V43L224 19" fill="none" stroke="var(--pc-ink)" stroke-width="4"/>
    <path d="M34 328L286 228" stroke="var(--pc-accent)" stroke-width="10"/>''',
    'albert_park': '''<path d="M0 35C94 76 67 110 154 137S228 202 194 244S151 311 257 360H0Z" fill="var(--pc-second)"/>
    <path d="M0 49C85 84 51 119 141 147S213 201 180 241S136 311 244 360" fill="none" stroke="var(--pc-paper)" stroke-width="6"/>
    <path d="M15 113H72M30 188H112M12 265H91M74 315H129" stroke="var(--pc-paper)" stroke-width="3"/>
    <path d="M155 42L181 111L207 42M160 111H202M225 129L244 180L263 129" fill="none" stroke="var(--pc-ink)" stroke-width="4"/>''',
    'shanghai': '''<path d="M22 157Q80 51 142 139Q196 46 264 151L222 175L143 153L65 177Z" fill="var(--pc-accent)"/>
    <path d="M23 157L143 153L264 151M143 153V305M66 176L108 306M222 175L177 305" fill="none" stroke="var(--pc-ink)" stroke-width="4"/>
    <path d="M42 318H248M68 335H273" stroke="var(--pc-second)" stroke-width="6"/>
    <path d="M38 153L73 123M73 168L111 112M177 162L199 113M219 164L237 132" stroke="var(--pc-paper)" stroke-width="3"/>''',
    'imola': '''<path d="M-20 338C42 223 118 302 165 223S131 118 215 49" fill="none" stroke="var(--pc-second)" stroke-width="24"/>
    <path d="M0 352C60 242 142 320 190 230S157 128 243 59" fill="none" stroke="var(--pc-ink)" stroke-width="8"/>
    <g fill="var(--pc-accent)"><path d="M30 48L17 149H43ZM72 35L56 166H88ZM111 51L97 155H125ZM251 175L237 285H265"/></g>
    <path d="M30 136V202M72 151V226M111 141V199M251 270V322" stroke="var(--pc-ink)" stroke-width="3"/>''',
    'monaco': '''<path d="M0 328L45 257L113 270L158 184L235 172L286 99" fill="none" stroke="var(--pc-ink)" stroke-width="14"/>
    <path d="M0 351L49 281L126 294L174 207L248 197L288 138" fill="none" stroke="var(--pc-accent)" stroke-width="5"/>
    <g fill="var(--pc-second)"><path d="M30 89Q75 58 121 89L102 113H49ZM130 116Q176 82 220 116L199 142H149ZM192 272Q234 242 275 272L256 297H210"/></g>
    <path d="M75 57V87M175 80V113M233 243V269" stroke="var(--pc-ink)" stroke-width="3"/>''',
    'villeneuve': _biosphere(),
    'catalunya': '''<path d="M12 66L126 28L98 143ZM144 30L269 93L118 144ZM14 91L85 157L22 270ZM101 170L260 111L244 259ZM30 285L102 185L143 328ZM121 183L238 277L162 333Z" fill="var(--pc-accent)"/>
    <path d="M27 84L101 51M142 57L239 101M42 179L35 242M151 180L226 150M88 250L134 316M170 232L215 275" fill="none" stroke="var(--pc-second)" stroke-width="10"/>
    <path d="M9 345L286 302" stroke="var(--pc-ink)" stroke-width="4"/>''',
    'red_bull_ring': '''<path d="M5 301L57 238L105 257L174 120L253 87L278 142L218 206L188 300Z" fill="none" stroke="var(--pc-ink)" stroke-width="13"/>
    <path d="M-10 134L84 103L137 129M-10 172L92 143L128 159M-10 213L93 182L111 188" fill="none" stroke="var(--pc-second)" stroke-width="13"/>
    <path d="M176 116L252 84L281 143" fill="none" stroke="var(--pc-accent)" stroke-width="5" stroke-dasharray="12 8"/>''',
    'silverstone': '''<path d="M9 226L67 118L124 154L184 60L267 160L219 211L146 193L88 243Z" fill="var(--pc-second)"/>
    <path d="M10 231L68 123L124 160L185 66L269 165M34 258L88 189L147 211L217 228" fill="none" stroke="var(--pc-ink)" stroke-width="5"/>
    <path d="M40 278H266M64 294H245M89 309H216" stroke="var(--pc-accent)" stroke-width="6"/>''',
    'hungaroring': '''<path d="M44 280V106H96V280M190 280V106H242V280M36 106H104M182 106H250" fill="none" stroke="var(--pc-ink)" stroke-width="7"/>
    <path d="M56 280V138H84V280M202 280V138H230V280M0 179Q70 104 143 210Q215 104 288 179M0 202Q70 126 143 232Q215 126 288 202M0 280H288" fill="none" stroke="var(--pc-second)" stroke-width="4"/>
    <path d="M22 175V280M120 183V280M165 183V280M266 175V280M0 316H288" stroke="var(--pc-accent)" stroke-width="3"/>''',
    'spa': '''<path d="M4 351L66 287L110 282L139 202L180 190L252 60" fill="none" stroke="var(--pc-ink)" stroke-width="36"/>
    <path d="M4 351L66 287L110 282L139 202L180 190L252 60" fill="none" stroke="var(--pc-paper)" stroke-width="25"/>
    <path d="M4 351L66 287L110 282L139 202L180 190L252 60" fill="none" stroke="var(--pc-accent)" stroke-width="5" stroke-dasharray="13 11"/>
    <path d="M33 43L10 124H56ZM82 72L61 145H103ZM157 31L133 114H181ZM230 224L208 309H252" fill="var(--pc-second)"/>''',
    'zandvoort': '''<path d="M20 278C72 82 232 77 262 177S167 327 90 264" fill="none" stroke="var(--pc-ink)" stroke-width="36"/>
    <path d="M20 278C72 82 232 77 262 177S167 327 90 264" fill="none" stroke="var(--pc-paper)" stroke-width="24"/>
    <path d="M20 278C72 82 232 77 262 177S167 327 90 264" fill="none" stroke="var(--pc-accent)" stroke-width="4" stroke-dasharray="12 8"/>
    <path d="M0 342Q105 282 288 329M29 326L22 296M40 321L48 284M53 316L66 295M221 324L226 293M232 327L249 300" fill="none" stroke="var(--pc-second)" stroke-width="3"/>''',
    'monza': '''<path d="M70 54C-7 78 5 281 78 307L183 308C266 284 277 81 192 54Z" fill="none" stroke="var(--pc-ink)" stroke-width="17"/>
    <path d="M70 54C-7 78 5 281 78 307L183 308C266 284 277 81 192 54Z" fill="none" stroke="var(--pc-paper)" stroke-width="7"/>
    <path d="M51 72L177 91L204 152L168 217L66 280" fill="none" stroke="var(--pc-accent)" stroke-width="8"/>
    <path d="M98 116V238M119 100V252M141 111V242" stroke="var(--pc-second)" stroke-width="7"/>''',
    'baku': '''<path d="M26 316V139H51V112H75V139H99V112H123V139H148V89H171V59H195V89H218V59H242V89H267V316Z" fill="var(--pc-second)"/>
    <path d="M45 315V207H106V315M169 315V176H235V315M161 132H252M37 178H135M118 270H156" fill="none" stroke="var(--pc-paper)" stroke-width="5"/>
    <path d="M-7 351L111 324L147 287L188 282L290 308" fill="none" stroke="var(--pc-accent)" stroke-width="11"/>''',
    'marina_bay': '''<path d="M53 306L65 117H96L105 306M119 306L130 102H159L171 306M187 306L198 93H227L238 306" fill="none" stroke="var(--pc-ink)" stroke-width="5"/>
    <path d="M25 95Q148 115 264 65L257 87Q148 135 37 114Z" fill="var(--pc-accent)"/>
    <path d="M0 328H288M0 344H288M72 154H93M138 139H158M205 131H224M71 191H95M136 179H161M203 170H226M69 229H98M134 218H164M201 210H229" stroke="var(--pc-second)" stroke-width="3"/>''',
    'vegas': '''<path d="M28 301V146H78V92H177V146H227V301Z" fill="none" stroke="var(--pc-accent)" stroke-width="5"/>
    <path d="M52 274V163H203V274ZM92 118H163M18 322H278M38 340H258" fill="none" stroke="var(--pc-ink)" stroke-width="3"/>
    <circle cx="245" cy="83" r="49" fill="var(--pc-paper)" stroke="var(--pc-second)" stroke-width="3"/>
    <path d="M201 63H288M198 84H293M202 105H287M220 39Q242 83 220 127M245 34V132M270 40Q248 83 270 126" fill="none" stroke="var(--pc-second)" stroke-width="2"/>
    <path d="M43 156V288M213 156V288" stroke="var(--pc-second)" stroke-width="5" stroke-linecap="round" stroke-dasharray="1 13"/>''',
    'losail': '''<path d="M52 319V71M146 319V39M238 319V82" fill="none" stroke="var(--pc-ink)" stroke-width="5"/>
    <path d="M23 73L52 46L82 73M116 40L146 12L177 40M208 84L238 56L269 84" fill="none" stroke="var(--pc-second)" stroke-width="6"/>
    <g fill="var(--pc-accent)"><path d="M24 77H38V88H24ZM46 66H60V77H46ZM68 77H82V88H68ZM117 44H131V55H117ZM139 32H153V43H139ZM161 44H175V55H161ZM209 88H223V99H209ZM231 76H245V87H231ZM253 88H267V99H253Z"/></g>
    <path d="M-3 344L278 282" stroke="var(--pc-accent)" stroke-width="13"/>''',
    'yas_marina': '''<path d="M17 261C14 159 74 87 173 80C223 80 267 112 283 168L262 284L75 298Z" fill="none" stroke="var(--pc-ink)" stroke-width="4"/>
    <path d="M31 207L166 84M25 243L208 91M48 280L244 112M92 294L267 142M150 290L278 177M204 286L271 216M49 132L198 287M81 106L250 279M123 87L278 242M170 83L283 196M28 174L139 294" fill="none" stroke="var(--pc-accent)" stroke-width="2.5"/>
    <path d="M0 329H288M0 344H288" stroke="var(--pc-second)" stroke-width="7"/>''',
    'madring': '''<path d="M18 304V166H56V143H108V120H179V143H231V166H269V304Z" fill="var(--pc-second)"/>
    <path d="M111 119L143 93L177 119M35 304V219H58V304M83 304V219Q100 188 117 219V304M133 304V198Q145 177 158 198V304M177 304V219Q194 188 211 219V304M238 304V219H255V304" fill="var(--pc-paper)" stroke="var(--pc-ink)" stroke-width="3"/>
    <path d="M0 333Q152 289 288 338" fill="none" stroke="var(--pc-accent)" stroke-width="12"/>''',
    'sepang': '''<path d="M21 153Q76 56 145 123Q204 53 271 151L223 179L144 147L68 179Z" fill="var(--pc-second)"/>
    <path d="M22 153L145 123L271 151M68 179L145 123L223 179M145 123V310M68 179L98 310M223 179L190 310" fill="none" stroke="var(--pc-ink)" stroke-width="4"/>
    <path d="M46 149L82 110M91 160L120 116M175 153L196 110M218 159L238 129M15 329H278" fill="none" stroke="var(--pc-accent)" stroke-width="4"/>''',
}


DESTINATIONS = {
    'miami': Destination(
        name=('Miami','Miami'),
        motif=('Linhas Art Déco de Miami','Miami Art Deco lines'),
        palette=('#d8eee8','#15494c','#cd5966','#e3af48'),
        artwork=ARTWORKS['miami'],
        frame='steps',
        photo_position='60% 58%',
        reference='https://tpddesignhouse.com/projects/formula-1-miami-paddock-club/',
    ),
    'suzuka': Destination(
        name=('Suzuka','Suzuka'),
        motif=('Roda-gigante e curvas de Suzuka','Suzuka Ferris wheel and bends'),
        palette=('#f8f3ec','#1b304b','#bd333e','#416c9d'),
        artwork=ARTWORKS['suzuka'],
        frame='orbit',
        photo_position='66% 58%',
        reference='https://www.alpinef1.com/news/behind-the-design-japanese-gp-race-poster',
    ),
    'rodriguez': Destination(
        name=('Cidade do México','Mexico City'),
        motif=('Arquibancadas e movimento muralista','Stadium terraces and muralist movement'),
        palette=('#f6e4d8','#184d41','#d19832','#a64b44'),
        artwork=ARTWORKS['rodriguez'],
        frame='stadium',
        photo_position='66% 58%',
        reference='https://pinchemoreno.myportfolio.com/ocesa-2015-formula-1-mexican-grand-prix',
    ),
    'interlagos': Destination(
        name=('São Paulo','São Paulo'),
        motif=('Curvas e zebras de Interlagos','Interlagos bends and kerbs'),
        palette=('#e2eee4','#174d42','#c53b3c','#d4aa39'),
        artwork=ARTWORKS['interlagos'],
        frame='curb',
        photo_position='68% 58%',
        reference='https://autodromodeinterlagos.prefeitura.sp.gov.br/w/nova-identidade-visual-do-autodromo-de-interlagos',
    ),
    'americas': Destination(
        name=('Austin','Austin'),
        motif=('A torre de observação do COTA','COTA observation tower'),
        palette=('#e8e1d4','#24465c','#bd453b','#738b79'),
        artwork=ARTWORKS['americas'],
        frame='frame',
        photo_position='68% 58%',
    ),
    'bahrain': Destination(
        name=('Sakhir','Sakhir'),
        motif=('A torre do circuito de Sakhir','Sakhir circuit tower'),
        palette=('#eadbc7','#493945','#ba5a43','#c4a683'),
        artwork=ARTWORKS['bahrain'],
        frame='diagonal',
        photo_position='60% 55%',
    ),
    'jeddah': Destination(
        name=('Jeddah','Jeddah'),
        motif=('O traçado junto à Corniche','The route beside the Corniche'),
        palette=('#dbe9e7','#214c55','#c59b55','#65a2aa'),
        artwork=ARTWORKS['jeddah'],
        frame='sweep',
        photo_position='64% 58%',
    ),
    'albert_park': Destination(
        name=('Melbourne','Melbourne'),
        motif=('A margem do lago de Albert Park','Albert Park lakeside'),
        palette=('#e2ece5','#244a49','#b7794b','#82adbd'),
        artwork=ARTWORKS['albert_park'],
        frame='sweep',
        photo_position='63% 62%',
    ),
    'shanghai': Destination(
        name=('Shanghai','Shanghai'),
        motif=('Coberturas de lótus do circuito','The circuit’s lotus-leaf canopies'),
        palette=('#f1e5d6','#4a3237','#af4640','#b19354'),
        artwork=ARTWORKS['shanghai'],
        frame='steps',
        photo_position='62% 58%',
        reference='https://tilke.de/portfolio/shanghai-international-circuit/',
    ),
    'imola': Destination(
        name=('Imola','Imola'),
        motif=('O Santerno e as curvas do parque','The Santerno and the park bends'),
        palette=('#e3e9db','#314a3b','#6c8a62','#7babb4'),
        artwork=ARTWORKS['imola'],
        frame='sweep',
        photo_position='65% 60%',
    ),
    'monaco': Destination(
        name=('Monte Carlo','Monte Carlo'),
        motif=('O porto e seus cais','The harbour and its quays'),
        palette=('#e4e9e4','#254955','#b35b4f','#74a2b0'),
        artwork=ARTWORKS['monaco'],
        frame='harbour',
        photo_position='64% 52%',
    ),
    'villeneuve': Destination(
        name=('Montreal','Montreal'),
        motif=('A Biosphère no Parc Jean-Drapeau','The Biosphère at Parc Jean-Drapeau'),
        palette=('#e6e9dc','#314e43','#af4942','#9caf98'),
        artwork=ARTWORKS['villeneuve'],
        frame='orbit',
        photo_position='65% 58%',
        reference='https://www.parcjeandrapeau.com/en/the-dome-biosphere-history/',
    ),
    'catalunya': Destination(
        name=('Barcelona','Barcelona'),
        motif=('Geometria do mosaico catalão','Catalan mosaic geometry'),
        palette=('#f0e4d0','#4c4638','#bf7850','#5c8290'),
        artwork=ARTWORKS['catalunya'],
        frame='diagonal',
        photo_position='68% 59%',
    ),
    'red_bull_ring': Destination(
        name=('Spielberg','Spielberg'),
        motif=('Curvas e planos da Estíria','Styrian bends and landscape planes'),
        palette=('#e3eadf','#314b3b','#b75543','#91ad8b'),
        artwork=ARTWORKS['red_bull_ring'],
        frame='slope',
        photo_position='65% 58%',
    ),
    'silverstone': Destination(
        name=('Silverstone','Silverstone'),
        motif=('A cobertura angular do Wing','The Wing’s angular roof'),
        palette=('#e2e7e7','#2c435c','#ab4e46','#879ba8'),
        artwork=ARTWORKS['silverstone'],
        frame='frame',
        photo_position='66% 59%',
    ),
    'hungaroring': Destination(
        name=('Budapeste','Budapest'),
        motif=('As pontes de Budapeste','Budapest’s bridges'),
        palette=('#e9e1d3','#3a4b4d','#ae6d4f','#8ba5a2'),
        artwork=ARTWORKS['hungaroring'],
        frame='diagonal',
        photo_position='65% 58%',
    ),
    'spa': Destination(
        name=('Spa-Francorchamps','Spa-Francorchamps'),
        motif=('A subida de Eau Rouge','The climb at Eau Rouge'),
        palette=('#e2e7d6','#294a3c','#ba6244','#779977'),
        artwork=ARTWORKS['spa'],
        frame='slope',
        photo_position='62% 58%',
    ),
    'zandvoort': Destination(
        name=('Zandvoort','Zandvoort'),
        motif=('Curvas inclinadas e dunas','Banked bends and dunes'),
        palette=('#ebe2d0','#354d59','#c7823f','#a69d74'),
        artwork=ARTWORKS['zandvoort'],
        frame='sweep',
        photo_position='64% 58%',
    ),
    'monza': Destination(
        name=('Monza','Monza'),
        motif=('O oval histórico no parque','The historic oval in the park'),
        palette=('#e4e9da','#314c3b','#b45a48','#7c9676'),
        artwork=ARTWORKS['monza'],
        frame='orbit',
        photo_position='66% 58%',
    ),
    'baku': Destination(
        name=('Baku','Baku'),
        motif=('As muralhas da cidade antiga','The old-city walls'),
        palette=('#eedfc7','#284954','#b66d46','#bba47c'),
        artwork=ARTWORKS['baku'],
        frame='steps',
        photo_position='65% 57%',
    ),
    'marina_bay': Destination(
        name=('Marina Bay','Marina Bay'),
        motif=('A arquitetura noturna de Marina Bay','Marina Bay’s night-time architecture'),
        palette=('#193b47','#f2e9d5','#d49a61','#75a5a9'),
        artwork=ARTWORKS['marina_bay'],
        frame='frame',
        photo_position='67% 59%',
    ),
    'vegas': Destination(
        name=('Las Vegas','Las Vegas'),
        motif=('Letreiros e a esfera de Las Vegas','Las Vegas marquees and sphere'),
        palette=('#1d304b','#f3e9d4','#c49a55','#b37983'),
        artwork=ARTWORKS['vegas'],
        frame='frame',
        photo_position='65% 56%',
    ),
    'losail': Destination(
        name=('Lusail','Lusail'),
        motif=('A iluminação da corrida noturna','The night race lighting'),
        palette=('#eae0d2','#533b4c','#bc9354','#967789'),
        artwork=ARTWORKS['losail'],
        frame='diagonal',
        photo_position='65% 58%',
    ),
    'yas_marina': Destination(
        name=('Abu Dhabi','Abu Dhabi'),
        motif=('A cobertura em malha de Yas Marina','Yas Marina’s lattice canopy'),
        palette=('#e6e7dd','#304f53','#9185a5','#75a9a3'),
        artwork=ARTWORKS['yas_marina'],
        frame='sweep',
        photo_position='65% 57%',
    ),
    'madring': Destination(
        name=('Madrid','Madrid'),
        motif=('A geometria da Puerta de Alcalá','The geometry of Puerta de Alcalá'),
        palette=('#eee0d3','#4c3e49','#b66e48','#ba9d89'),
        artwork=ARTWORKS['madring'],
        frame='steps',
        photo_position='64% 56%',
        reference='https://www.esmadrid.com/en/tourist-information/puerta-alcala',
    ),
    'sepang': Destination(
        name=('Sepang','Sepang'),
        motif=('As coberturas das arquibancadas','The grandstand canopies'),
        palette=('#e3ebda','#28534a','#c69c46','#8fae87'),
        artwork=ARTWORKS['sepang'],
        frame='diagonal',
        photo_position='65% 58%',
        reference='https://www.sepangcircuit.com/architecture',
    ),
}


def artwork_svg(circuit_id):
    destination = DESTINATIONS.get(circuit_id)
    if destination is None:
        return ''
    return ('<svg class="pc-destination-art" data-place-art="{}" viewBox="0 0 300 360" '
            'aria-hidden="true" focusable="false" xmlns="http://www.w3.org/2000/svg">'
            '<g stroke-linecap="round" stroke-linejoin="round">{}</g></svg>').format(circuit_id, destination.artwork)
