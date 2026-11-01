# Fan Journey

[Português](../JORNADA_DO_FA.md)

Approved composition C guides the entire product: Races, Drivers, Championship, Podium chances, Lab score and How it works. The blue/white/navy/red palette and Abril Fatface/Lato fonts remain. Implementation uses existing data, not the illustrative numbers in the concept board.

## Navigation

Six destinations appear in the bottom navigation, with icons, labels and visible selection. The native control supports keyboard interaction. The page reserves bottom space so the menu does not remove content. Season and GP selectors appear at the top of context-dependent areas. The selector includes every event; the visual ribbon shows nearby events and identifies the selected one. Mobile emphasizes the selected GP and its neighbors.

Races retains six chapters through tabs: Summary, Sessions and laps, Tyres and pit stops, Weather, At this track and Teams. The image and outline precede the podium. Tabs preserve existing routes and avoid opening every table in a single long page. Drivers retains highlights, profiles and duels with independent filters. Championship retains every published driver and constructor row, now in sequence. Sources, limitations and documents remain accessible throughout the product.

## Optional cards

In Podium chances, **Open the GP cards** opens an optional dialog. Direct links can use `?tela=Previsões&temporada=2026&gp=19&cartas=1&lang=en`. Close with X, Escape or the table link. Closing or changing GP clears the opening state. Normal navigation never opens the dialog automatically.

Drivers and percentages come from the selected GP's stored favorites, including ties. There is no random draw, recalculation or P1/P2/P3 prediction. Team names follow the period's record. Missing forecasts do not produce cards. Retrospective studies are labeled accordingly. Drivers without artwork receive a helmet symbol. Mobile stacks cards in a scrollable dialog.

Verstappen, Hamilton and Russell illustrations are AI-generated decorative art, not photographs, endorsements or outcomes. Credits: [card artwork](../../dashboard_assets/tarot/ATTRIBUTION.md). Probabilities remain individual and never predict finishing order.

## Preserved limits

Navigation remains offline: it neither collects data, trains nor runs inference. Registered forecasts, retrospective analysis and later observations retain their meanings. Frozen v1, its 15 inputs and previous emissions remain preserved. A new interface does not fill provider gaps; those remain explicit.
