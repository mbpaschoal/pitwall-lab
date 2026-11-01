"""Visual presentation must not invent observed places or missing evaluations."""
import unittest
from pitwall.dashboard.fan_views import podium, forecast_rows, performance_cards, condition_rows, hero, HERO_IMAGES
from pitwall.i18n import set_language


class FanCompositionTests(unittest.TestCase):
    def setUp(self):
        set_language('pt')

    def test_driver_banners_require_documented_real_identity(self):
        for preset in ('rain','helmet','car'):
            rendered=hero('Título',image=preset)
            self.assertIn('data-driver-id="'+HERO_IMAGES[preset]['driver_id']+'"',rendered)
            self.assertIn(HERO_IMAGES[preset]['name'],rendered)
            self.assertNotIn('Ilustração IA',rendered)
            self.assertIn('<a class="fan-art-label"',rendered)
        with self.assertRaises(KeyError):hero('Título',image='invented_driver')

    def test_photo_mime_and_identity_survive_english_rendering(self):
        set_language('en')
        rendered=hero('Chances de pódio',image='car')
        self.assertIn('data:image/jpeg;base64,',rendered)
        self.assertIn('alt="Sergio Pérez in the Red Bull RB18 at Miami on 7 May 2022.',rendered)
        self.assertIn('Miami 2022',rendered)

    def test_podium_never_turns_forecast_order_into_observed_places(self):
        rows=[dict(id='norris',name='Lando Norris',team='McLaren',probability=.9)]
        rendered=podium(rows,2026)
        self.assertNotIn('fan-podium-place',rendered)
        self.assertIn('Resultado ainda indisponível',rendered)

    def test_observed_podium_is_sorted_by_its_actual_positions(self):
        rows=[dict(id='max_verstappen',name='Max',team='Red Bull',position=3),
              dict(id='antonelli',name='Kimi',team='Mercedes',position=1),
              dict(id='leclerc',name='Charles',team='Ferrari',position=2)]
        rendered=podium(rows,2026)
        self.assertLess(rendered.index('fan-place-2'),rendered.index('fan-place-1'))
        self.assertLess(rendered.index('fan-place-1'),rendered.index('fan-place-3'))
        self.assertIn('piloto=antonelli',rendered)

    def test_unknown_evaluations_do_not_become_zero_scores(self):
        rows=[dict(rodada=18,corrida='United States Grand Prix',modelo=2,classificacao=2)]
        races=[dict(rodada=17,corrida='Singapore Grand Prix'),
               dict(rodada=18,corrida='United States Grand Prix',estado_previsao='previsao_registrada'),
               dict(rodada=19,corrida='Mexico City Grand Prix',estado_previsao='previsao_registrada')]
        rendered=performance_cards(rows,races,2026)
        self.assertEqual(rendered.count('class="fan-hit"'),4)
        self.assertIn('Sem previsão registrada',rendered)
        self.assertIn('Corrida aguardada',rendered)
        self.assertNotIn('0 de 3',rendered)

    def test_retrospective_cards_do_not_claim_prospective_predictions(self):
        row=dict(rodada=1,corrida='Bahrain Grand Prix',modelo=2,classificacao=3)
        rendered=performance_cards([row],[dict(rodada=1,corrida='Bahrain Grand Prix')],2024)
        self.assertIn('Estudo retrospectivo com dados históricos.',rendered)
        self.assertNotIn('Somente previsões registradas',rendered)

    def test_count_metric_has_visible_relative_bars_without_a_fake_percentage(self):
        row=dict(score=3,rank=1,driver_id='norris',driver_name='Lando Norris',starts=8)
        rendered=condition_rows([row],'wins',{'norris':'?piloto=norris'})
        self.assertRegex(rendered,r'width:100(?:\.0+)?%')
        self.assertIn('<em>3</em>',rendered)
        self.assertNotIn('<em>3.00</em>',rendered)

    def test_forecast_rows_escape_names_and_keep_individual_probabilities(self):
        html=forecast_rows([dict(id='unknown',name='<driver>',team='Team',probability=.682)],2026)
        self.assertIn('&lt;driver&gt;',html)
        self.assertIn('68,2%',html)
        self.assertNotIn('fan-place-1',html)


    def test_comparison_tooltip_uses_the_selected_language(self):
        set_language('en')
        row=dict(score=.375,rank=1,driver_id='norris',driver_name='Lando Norris',starts=8)
        comparisons={'norris':[dict(label='Chuva',score=.375,starts=8,maximum=1)]}
        html=condition_rows([row],'win_rate',{'norris':'?piloto=norris'},comparisons=comparisons)
        self.assertIn('title="Rain · 8 starts"',html)
        self.assertNotIn('title="Chuva',html)

if __name__=='__main__':unittest.main()
