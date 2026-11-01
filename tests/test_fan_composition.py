"""Visual presentation must not invent observed places or missing evaluations."""
import unittest
from pitwall.dashboard.fan_views import podium, forecast_rows, performance_cards, condition_rows
from pitwall.i18n import set_language


class FanCompositionTests(unittest.TestCase):
    def setUp(self):
        set_language('pt')

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

    def test_count_metric_has_visible_relative_bars_without_a_fake_percentage(self):
        row=dict(score=3,rank=1,driver_id='norris',driver_name='Lando Norris',starts=8)
        rendered=condition_rows([row],'wins',{'norris':'?piloto=norris'})
        self.assertIn('width:100.0%',rendered)
        self.assertIn('<em>3</em>',rendered)
        self.assertNotIn('<em>3.00</em>',rendered)

    def test_forecast_rows_escape_names_and_keep_individual_probabilities(self):
        html=forecast_rows([dict(id='unknown',name='<driver>',team='Team',probability=.682)],2026)
        self.assertIn('&lt;driver&gt;',html)
        self.assertIn('68,2%',html)
        self.assertNotIn('fan-place-1',html)


if __name__=='__main__':unittest.main()
