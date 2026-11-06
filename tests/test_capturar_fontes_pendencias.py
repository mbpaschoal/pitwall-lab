import hashlib
from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from capturar_fontes_pendencias import capturar


class CapturaTest(unittest.TestCase):
    def rate_limited_receipt(self, root, retry_after):
        raw=b'provider limited';(root/'limited.bin').write_bytes(raw)
        receipt=dict(id='limited',url='https://www.fia.com/limited',arquivo='limited.bin',
                     sha256=hashlib.sha256(raw).hexdigest(),status=429,
                     obtido_em_utc='2026-11-05T11:00:00+00:00',headers={'retry-after':retry_after})
        (root/'recibos.json').write_text(json.dumps([receipt]))
        return (root/'recibos.json').read_bytes()

    def test_resume_observes_prior_rate_limit_before_querying_other_urls(self):
        for retry in ('3600','Thu, 05 Nov 2026 12:00:00 GMT','invalid'):
            with self.subTest(retry=retry),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);before=self.rate_limited_receipt(root,retry)
                with patch('capturar_fontes_pendencias.datetime') as clock, \
                     patch('capturar_fontes_pendencias.time.sleep'), \
                     patch('capturar_fontes_pendencias.urlopen',side_effect=AssertionError('No request during cooldown')) as opening:
                    clock.now.return_value=datetime(2026,11,5,11,30,tzinfo=timezone.utc)
                    clock.fromisoformat.side_effect=datetime.fromisoformat
                    with self.assertRaisesRegex(RuntimeError,'Retry-After'):
                        capturar([dict(id='next',url='https://www.fia.com/next')],root)
                    opening.assert_not_called()
                self.assertEqual((root/'recibos.json').read_bytes(),before)
                self.assertEqual((root/'limited.bin').read_bytes(),b'provider limited')

    def test_after_rate_limit_next_capture_keeps_prior_failure_evidence(self):
        class Response(BytesIO):
            status=200;url='https://www.fia.com/next';headers={}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.rate_limited_receipt(root,'3600')
            previous=json.loads((root/'recibos.json').read_text())[0]
            with patch('capturar_fontes_pendencias.datetime') as clock, \
                 patch('capturar_fontes_pendencias.time.sleep'), \
                 patch('capturar_fontes_pendencias.urlopen',return_value=Response(b'next source')) as opening:
                clock.now.return_value=datetime(2026,11,5,12,1,tzinfo=timezone.utc)
                clock.fromisoformat.side_effect=datetime.fromisoformat
                receipts=capturar([dict(id='next',url='https://www.fia.com/next')],root)
            opening.assert_called_once();self.assertEqual(receipts[0],previous)
            self.assertEqual(receipts[1]['status'],200)
            self.assertEqual((root/'limited.bin').read_bytes(),b'provider limited')

    def test_cache_valido_nao_consulta_e_hash_divergente_falha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);raw=b'fonte original';(root/'a.bin').write_bytes(raw)
            item={'id':'a','url':'https://www.fia.com/documento','arquivo':'a.bin','sha256':hashlib.sha256(raw).hexdigest(),'status':200}
            (root/'recibos.json').write_text(json.dumps([item]))
            with patch('capturar_fontes_pendencias.urlopen',side_effect=AssertionError('rede indevida')):
                self.assertEqual(capturar([item],root),[item])
                (root/'a.bin').write_bytes(b'outros bytes')
                with self.assertRaisesRegex(ValueError,'Cache divergente'):capturar([item],root)

    def test_host_nao_admitido_nao_e_consultado(self):
        with tempfile.TemporaryDirectory() as tmp, patch('capturar_fontes_pendencias.urlopen',side_effect=AssertionError('rede indevida')):
            with self.assertRaisesRegex(ValueError,'Origem não admitida'):
                capturar([{'id':'x','url':'https://example.org/'}],tmp)
