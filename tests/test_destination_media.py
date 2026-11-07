"""Circuit identity, source integrity and safe fallback for editorial covers."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from pitwall.dashboard.destination_art import DESTINATIONS, artwork_svg
from pitwall.dashboard.media import circuit_photo_source, circuit_static_path
from pitwall.dashboard.postcards import cover
from pitwall.i18n import set_language

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / 'exportar_dashboard.py').is_file():
    from exportar_dashboard import RUNTIME_WORKTREE as DELIVERY_ALLOWLIST
else:
    # The portable runtime includes its explicit member list, not the builder.
    DELIVERY_ALLOWLIST = (ROOT / 'ARQUIVOS_PUBLICACAO.txt').read_text().splitlines()


class DestinationMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = b'fixture photograph bytes'
        self.photo = dict(caminho='dashboard_assets/circuit/test.jpg',
                          sha256=hashlib.sha256(self.raw).hexdigest())
        self.source = self.root / self.photo['caminho']
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(self.raw)
        self.static = self.root / circuit_static_path('test', self.photo)
        self.static.parent.mkdir(parents=True)
        self.static.write_bytes(self.raw)
        set_language('pt')
        self.addCleanup(set_language, 'pt')

    def test_all_approved_circuits_have_distinct_safe_art_and_exact_static_bytes(self):
        catalog = json.loads((ROOT / 'dashboard_assets/circuit/catalogo_visual.json').read_text())['circuitos']
        self.assertEqual(set(DESTINATIONS), set(catalog))
        self.assertEqual(len({d.artwork for d in DESTINATIONS.values()}), len(catalog))
        for cid, assets in catalog.items():
            svg = ET.fromstring(artwork_svg(cid))
            self.assertEqual(svg.attrib['aria-hidden'], 'true')
            self.assertFalse(any(el.tag.split('}')[-1] in ('script', 'image', 'foreignObject') for el in svg.iter()))
            photo = assets['foto']
            static = circuit_static_path(cid, photo)
            self.assertIn(static, DELIVERY_ALLOWLIST)
            self.assertEqual(hashlib.sha256((ROOT/static).read_bytes()).hexdigest(), photo['sha256'])
            self.assertEqual((ROOT/static).read_bytes(), (ROOT/photo['caminho']).read_bytes())
            self.assertEqual(circuit_photo_source(ROOT,cid,photo), 'app/'+static)

    def test_missing_or_corrupt_copy_uses_only_the_verified_original(self):
        self.static.write_bytes(b'wrong')
        self.assertEqual(circuit_photo_source(self.root,'test',self.photo), 'data:image/jpeg;base64,Zml4dHVyZSBwaG90b2dyYXBoIGJ5dGVz')
        self.static.unlink()
        self.assertTrue(circuit_photo_source(self.root,'test',self.photo).startswith('data:image/jpeg;'))
        self.source.write_bytes(b'wrong original')
        self.assertEqual(circuit_photo_source(self.root,'test',self.photo), '')

    def test_external_paths_and_symlinks_cannot_become_cover_images(self):
        for cid, photo in [('../test',self.photo),('test',dict(self.photo,caminho='../outside.jpg')),
                           ('test',dict(self.photo,sha256='invalid'))]:
            self.assertEqual(circuit_photo_source(self.root,cid,photo), '')
        self.source.unlink()
        self.source.symlink_to(self.static)
        self.assertEqual(circuit_photo_source(self.root,'test',self.photo), '')
        self.source.unlink(); self.source.write_bytes(self.raw)
        self.static.unlink(); self.static.symlink_to(self.source)
        self.assertTrue(circuit_photo_source(self.root,'test',self.photo).startswith('data:image/jpeg;'))

    def test_cover_keeps_inputs_and_sealed_forecast_text_in_both_languages(self):
        race=dict(corrida='Mexico City Grand Prix',circuito_id='rodriguez',
                  circuito_nome='Autódromo Hermanos Rodríguez',data='2026-11-01')
        assets=dict(foto=dict(self.photo,autor='<script>bad</script>',pagina='javascript:bad'))
        before=copy.deepcopy((race,assets))
        for lang, heading in [('pt','Previsões'),('en','Predictions')]:
            set_language(lang)
            html=cover(race,2026,forecast=True,assets=assets,root=self.root)
            self.assertIn('<h1>'+heading+'</h1>',html)
            self.assertIn('data-place="rodriguez"',html)
            self.assertNotIn('<script>',html)
            self.assertNotIn('href="javascript:',html)
            self.assertNotIn('%',html.split('class="pc-copy')[1].split('</div>')[0])
        self.assertEqual((race,assets),before)


if __name__ == '__main__':
    unittest.main()
