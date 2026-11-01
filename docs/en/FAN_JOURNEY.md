# Fan Journey

[Português](../JORNADA_DO_FA.md)

Approved composition C guides the entire product: Races, Drivers, Championship, Podium chances, Lab score and How it works. The blue/white/navy/red palette and Abril Fatface/Lato fonts remain. Implementation uses existing data, not the illustrative numbers in the concept board.

## Composition C across all six screens

The logo, season, GP and search share one compact header. Language flags remain at the top right. A nearby-race ribbon and six-item bottom navigation follow the approved composition.

1. **Races:** title and date over the circuit image, map on the right, observed portrait podium in visual 2–1–3 order next to circuit facts and weather.
2. **Drivers:** identified Lando Norris photograph, a direct question, condition shortcuts and portrait rankings with bars. Real ties stay tied; full rankings, criteria, individual profiles and duels remain accessible.
3. **Championship:** image banner, season progress and complete standings with portraits and team identifiers. No source rows are removed.
4. **Podium chances:** racing image and before/after timeline, individual probability bars, observed result when published and optional tarot cards.
5. **Lab results:** racing image, per-GP visual comparisons with qualifying and two insight cards. Missing forecasts are not scored zero and future races have no observed result. One evaluated race is never presented as six evaluated races to imitate the mockup.
6. **How it works:** identified Max Verstappen photograph, three illustrated steps and two document links. Technical detail stays in an expander which opens when following a document link.

Driver banners use identified photographs of real people. AI circuit illustrations and tarot art retain their own labels. Portraits do not establish a driver's historical uniform or team. [Image credits](../../dashboard_assets/fan/ATTRIBUTION.md) record sources and rights. The mockup guides composition and navigation; displayed figures come from real artifacts, without copying its fictional values.

## Navigation

Six destinations appear in the bottom navigation, with icons, labels and visible selection. The native control supports keyboard interaction. The page reserves bottom space so the menu does not remove content. Season and GP selectors appear at the top of context-dependent areas. The selector includes every event; the visual ribbon shows nearby events and identifies the selected one. Mobile emphasizes the selected GP and its neighbors.

Races retains six chapters through tabs: Summary, Sessions and laps, Tyres and pit stops, Weather, At this track and Teams. The image and outline precede the podium. Tabs preserve existing routes and avoid opening every table in a single long page. Drivers retains highlights, profiles and duels with independent filters. Championship retains every published driver and constructor row, now in sequence. Sources, limitations and documents remain accessible throughout the product.

## Optional cards

In Podium chances, **Open the GP cards** opens an optional dialog. Direct links can use `?tela=Previsões&temporada=2026&gp=19&cartas=1&lang=en`. Close with X, Escape or the table link. Closing or changing GP clears the opening state. Normal navigation never opens the dialog automatically.

Drivers come from the selected GP's stored favorites, including ties. Cards show only artwork, name and team; percentages remain in the forecast table. There is no random draw, recalculation or P1/P2/P3 prediction. Team names follow the period's record. Missing forecasts do not produce cards. Retrospective studies are labeled accordingly. Drivers without artwork matching the period's team receive a helmet symbol. Mobile stacks cards in a scrollable dialog.

Verstappen, Hamilton and Russell illustrations are AI-generated decorative art, not photographs, endorsements or outcomes. Credits: [card artwork](../../dashboard_assets/tarot/ATTRIBUTION.md). Probabilities remain individual and never predict finishing order.

## Preserved limits

Navigation remains offline: it neither collects data, trains nor runs inference. Registered forecasts, retrospective analysis and later observations retain their meanings. Frozen v1, its 15 inputs and previous emissions remain preserved. A new interface does not fill provider gaps; those remain explicit.
