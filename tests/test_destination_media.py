"""Circuit identity, source integrity and safe fallback for editorial covers."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pitwall.dashboard.destination_art import DESTINATIONS
from pitwall.dashboard.illustrations import illustration, CATALOG, STYLE
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
        gouaches = json.loads((ROOT / CATALOG).read_text())
        self.assertEqual(gouaches['style'], STYLE)
        self.assertTrue(gouaches['complete'])
        self.assertEqual(set(gouaches['circuits']), set(catalog))
        self.assertEqual(len({a['sha256'] for a in gouaches['circuits'].values()}), len(catalog))
        for cid, assets in catalog.items():
            art = illustration(ROOT, cid)
            self.assertIsNotNone(art, cid)
            self.assertIn(art['path'], DELIVERY_ALLOWLIST)
            self.assertEqual((art['width'], art['height']), (1536, 1024))
            self.assertTrue(art['reference_urls'])
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


class GouacheIdentityTests(unittest.TestCase):
    def setUp(self):
        self.addCleanup(set_language, 'pt')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = json.loads((ROOT / CATALOG).read_text())['circuits']['sepang']
        self.raw = (ROOT / source['path']).read_bytes()
        digest = hashlib.sha256(self.raw).hexdigest()
        self.spec = dict(source, circuit_id='test', path='static/pitwall-art/gouache/test-'+digest[:12]+'.png')
        self.path = self.root / self.spec['path']
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(self.raw)
        self.catalogue = self.root / CATALOG
        self.catalogue.parent.mkdir()
        self.write()

    def write(self, spec=None, **updates):
        self.catalogue.write_text(json.dumps(dict(schema=1, style=STYLE, circuits={'test':spec or self.spec}, **updates)))

    def test_only_the_matching_circuit_original_is_admitted(self):
        art = illustration(self.root, 'test')
        self.assertEqual(art['src'], 'app/'+self.spec['path'])
        self.assertIsNone(illustration(self.root, 'other'))
        self.write(dict(self.spec, circuit_id='other'))
        self.assertIsNone(illustration(self.root, 'test'))

    def test_tampered_missing_or_wrong_dimension_art_has_no_photo_substitute(self):
        self.path.write_bytes(self.raw[:-1]+bytes([self.raw[-1]^1]))
        self.assertIsNone(illustration(self.root, 'test'))
        self.path.write_bytes(self.raw)
        self.write(dict(self.spec, width=self.spec['width']+2))
        self.assertIsNone(illustration(self.root, 'test'))
        self.write()
        self.path.unlink()
        self.assertIsNone(illustration(self.root, 'test'))

    def test_path_escape_remote_url_and_symlinks_are_rejected(self):
        self.assertIsNone(illustration(self.root, '../test'))
        for path in ['../outside.png', 'https://example.invalid/photo.png', self.spec['path'].replace('test-', 'other-')]:
            self.write(dict(self.spec, path=path))
            self.assertIsNone(illustration(self.root, 'test'))
        self.write()
        self.path.unlink()
        source = self.root / 'original.png'; source.write_bytes(self.raw)
        self.path.symlink_to(source)
        self.assertIsNone(illustration(self.root, 'test'))

    def test_malformed_catalogue_and_metadata_fail_closed(self):
        for value in [[], {}, {'schema':True,'style':STYLE,'circuits':{'test':self.spec}}]:
            self.catalogue.write_text(json.dumps(value))
            self.assertIsNone(illustration(self.root, 'test'))
        for updates in [dict(alt='xx'),dict(alt=['one']),dict(reference_urls=None),dict(sha256='bad')]:
            self.write(dict(self.spec, **updates))
            self.assertIsNone(illustration(self.root, 'test'))

    def test_full_scene_cover_escapes_text_and_leaves_forecasts_sealed(self):
        before=copy.deepcopy(self.spec)
        self.write(dict(self.spec, alt=['<script>bad</script>','<bad>'],reference_urls=['javascript:bad']))
        race=dict(corrida='Test Grand Prix',circuito_id='test',circuito_nome='Test Circuit',data='2026-11-01')
        for lang, heading in [('pt','Previsões'),('en','Predictions')]:
            set_language(lang)
            html=cover(race,2026,forecast=True,root=self.root)
            self.assertIn('<h1>'+heading+'</h1>',html)
            self.assertIn('class="pc-illustration"',html)
            self.assertNotIn('pc-photo',html)
            self.assertNotIn('<script>',html)
            self.assertNotIn('href="javascript:',html)
            self.assertNotIn('%',html)
        set_language('pt')
        self.assertEqual(self.spec,before)


if __name__ == '__main__':
    unittest.main()
