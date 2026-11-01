"""Visual presentation must not invent observed places or missing evaluations."""
import unittest
from pitwall.dashboard.fan_views import podium, forecast_rows, performance_cards, condition_rows, hero, HERO_IMAGES, circuit_details
from pitwall.i18n import set_language
from pitwall.dashboard.journey import race_identity


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

    def test_compact_comparison_keeps_identity_without_a_second_heading(self):
        rendered=podium([dict(id='antonelli',name='Andrea Kimi Antonelli',team='Mercedes',position=1)],2026,compact=True)
        self.assertNotIn('<h2>',rendered)
        self.assertIn('aria-label="Pódio da corrida"',rendered)
        self.assertIn('alt="Andrea Kimi Antonelli"',rendered)
        self.assertIn('>Antonelli</strong>',rendered)

    def test_circuit_summary_keeps_weather_before_optional_details(self):
        rendered=circuit_details(dict(comprimento_km=5.513,curvas=20,voltas=56),
                                 dict(corrida_efetiva=dict(air_temperature=27.1)))
        self.assertLess(rendered.index('class="fan-weather"'),rendered.index('class="fan-circuit-more"'))
        self.assertIn('27,1 °C',rendered)
        self.assertIn('Ar durante a corrida · OpenF1',rendered)

    def test_results_use_country_cues_without_inventing_a_known_country(self):
        self.assertEqual(race_identity('Bahrain in Malaysia Grand Prix'),('', 'Bahrain in Malaysia'))
        self.assertEqual(race_identity('Spanish Grand Prix'),('🇪🇸', 'Espanha'))
        rows=[dict(rodada=18,corrida='United States Grand Prix',modelo=2,classificacao=2)]
        rendered=performance_cards(rows,[dict(rodada=18,corrida='United States Grand Prix')],2026)
        self.assertIn('🇺🇸',rendered)
        self.assertIn('>EUA</strong>',rendered)
        self.assertIn('title="United States Grand Prix"',rendered)
        self.assertIn('Empate na corrida avaliada',rendered)
        self.assertIn('fan-results-legend',rendered)

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
