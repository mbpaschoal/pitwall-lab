/* Sidebar/card bridge also installs beside the pre-0.13 motion singleton. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallEditorial) { w.__pitwallEditorial.refresh(); return; }
  const preference = w.matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = () => {
    try { return preference.matches || w.sessionStorage.getItem('pitwall-motion-disabled') === 'true'; }
    catch (_) { return preference.matches; }
  };
  const deckMemory = new Map();
  function savedDeckState(key, count) {
    if (!deckMemory.has(key)) {
      let saved;
      try { saved = JSON.parse(w.sessionStorage.getItem('pitwall-deck-' + key)); } catch (_) {}
      deckMemory.set(key, Array.isArray(saved) && saved.length === count && saved.every(v => typeof v === 'boolean') ? saved : Array(count).fill(false));
    }
    return deckMemory.get(key);
  }
  function deckState(deck) {
    return savedDeckState(deck.dataset.deckKey, deck.querySelectorAll('.pw-sealed-card').length);
  }
  function refreshDeck(deck, focusIndex = null, animate = false) {
    const states = deckState(deck), cards = [...deck.querySelectorAll('.pw-sealed-card')];
    for (const [index, card] of cards.entries()) {
      const shown = states[index], slot = card.querySelector('.pw-revealed-face');
      // Streamlit may reuse the card node while replacing Markdown descendants.
      // Restore a revealed face after that replacement as well as on a flip.
      if (card.dataset.shown !== String(shown) || (shown && !slot.querySelector('[data-tarot-hide]'))) {
        if (shown) {
          const face = d.createElement('template');
          // Only the escaped server-rendered face is accepted; never a URL or client input.
          face.innerHTML = card.querySelector('template').dataset.pwFace;
          slot.replaceChildren(face.content.cloneNode(true));
        }
        else slot.replaceChildren();
        card.querySelector('[data-tarot-reveal]').hidden = shown;
        slot.hidden = !shown;
        card.dataset.shown = String(shown);
        if (animate && index === focusIndex && !reduced())
          (shown ? slot : card.querySelector('[data-tarot-reveal]')).animate(
            [{transform:'rotateY(-90deg)'},{transform:'rotateY(0)'}], {duration:240,easing:'ease-out'});
      }
    }
    const count = states.filter(Boolean).length;
    for (const details of d.querySelectorAll('.st-key-forecast-details,.st-key-forecast-audit'))
      details.dataset.pwUnlocked = String(states.length > 0 && count === states.length);
    if (focusIndex !== null) cards[focusIndex]?.querySelector(states[focusIndex] ? '[data-tarot-hide]' : '[data-tarot-reveal]')?.focus({preventScroll:true});
  }
  function refresh() {
    for (const button of d.querySelectorAll('.st-key-pw-sidebar-menu button[kind]')) {
      if (button.getAttribute('kind') === 'primary') button.setAttribute('aria-current','page');
      else button.removeAttribute('aria-current');
    }
    for (const deck of d.querySelectorAll('[data-deck-key]')) refreshDeck(deck);
    const explorer = d.querySelector('.st-key-pw-sidebar-menu details');
    if (explorer &&
        d.querySelectorAll('.pw-nav-fallback').length === 15 &&
        d.querySelector('.stApp')?.dataset.testScriptState === 'notRunning') {
      explorer.dataset.pwReady = 'true';
      if (!w.matchMedia('(max-width:800px)').matches && !explorer.open)
        explorer.querySelector('summary')?.click();
    }
  }
  d.addEventListener('click', event => {
    const tarot = event.target.closest('[data-tarot-reveal],[data-tarot-hide]');
    if (tarot) {
      const deck = tarot.closest('[data-deck-key]'), card = tarot.closest('.pw-sealed-card');
      const states = deckState(deck), index = Number(card.dataset.cardIndex);
      states[index] = !states[index];
      try { w.sessionStorage.setItem('pitwall-deck-' + deck.dataset.deckKey, JSON.stringify(states)); } catch (_) {}
      refreshDeck(deck, index, true);
      return;
    }
    if (event.target.closest('.st-key-pw-sidebar-menu button') && w.matchMedia('(max-width:800px)').matches) {
      const explorer = event.target.closest('details');
      if (explorer?.open) w.setTimeout(() => {
        if (explorer.isConnected && explorer.open) explorer.querySelector('summary')?.click();
      }, 0);
    }
  });
  d.addEventListener('toggle', event => {
    if (event.target.matches('.st-key-pw-sidebar-menu details') &&
        !event.target.open && !w.matchMedia('(max-width:800px)').matches) refresh();
  }, true);
  new w.MutationObserver(records => {
    if (records.some(r => [...r.addedNodes,...r.removedNodes].some(n => n.nodeType === 1))) refresh();
  }).observe(d.body,{childList:true,subtree:true});
  const app = d.querySelector('.stApp');
  if (app) new w.MutationObserver(refresh).observe(app,{attributes:true,attributeFilter:['data-test-script-state']});
  w.addEventListener('resize',refresh);
  w.__pitwallEditorial = {refresh, readDeckState:savedDeckState};
  refresh();
})();

/* Install dialog state beside an editorial bridge already loaded in an older tab. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallTarotDialog) { w.__pitwallTarotDialog.refresh(); return; }
  function refresh() {
    for (const context of d.querySelectorAll('[data-pw-deck-context]')) {
      const key = context.dataset.pwDeckContext, count = Number(context.dataset.deckSize);
      let states;
      if (w.__pitwallEditorial?.readDeckState) states = w.__pitwallEditorial.readDeckState(key, count);
      else try { states = JSON.parse(w.sessionStorage.getItem('pitwall-deck-' + key)); } catch (_) {}
      const unlocked = count > 0 && Array.isArray(states) && states.length === count && states.every(value => value === true);
      for (const details of d.querySelectorAll('.st-key-forecast-details,.st-key-forecast-audit'))
        details.dataset.pwUnlocked = String(unlocked);
    }
  }
  new w.MutationObserver(records => {
    if (records.some(r => [...r.addedNodes,...r.removedNodes].some(n => n.nodeType === 1))) refresh();
  }).observe(d.body,{childList:true,subtree:true});
  w.__pitwallTarotDialog = {refresh};
  refresh();
})();

/* Local adaptation of motion principles; no upstream engine or external calls. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallMotion) { w.__pitwallMotion.refresh(); return; }
  const preference = w.matchMedia('(prefers-reduced-motion: reduce)');
  let disabled = false, seenMethod = false;
  try { disabled = w.sessionStorage.getItem('pitwall-motion-disabled') === 'true'; } catch (_) {}
  const reduced = () => disabled || preference.matches;
  // The dock occupies its own viewport area; content cannot scroll behind it.
  let layoutPending = false, observedDock = null, observedMain = null;
  const resizeObserver = new w.ResizeObserver(scheduleLayout);
  function scheduleLayout() {
    if (layoutPending) return;
    layoutPending = true;
    w.requestAnimationFrame(() => {
      layoutPending = false;
      const main = d.querySelector('.stMain'), dock = d.querySelector('.st-key-journey-navigation');
      if (d.querySelector('.st-key-pw-shell')) {
        d.documentElement.style.removeProperty('--pw-content-max-height');
        return;
      }
      if (!main || !dock) return;
      for (const [next,old] of [[dock,observedDock],[main,observedMain]]) {
        if (next !== old) { if (old) resizeObserver.unobserve(old); resizeObserver.observe(next); }
      }
      observedDock = dock; observedMain = main;
      const viewportEnd = w.visualViewport ? w.visualViewport.offsetTop + w.visualViewport.height : w.innerHeight;
      const height = Math.max(0, Math.floor(Math.min(dock.getBoundingClientRect().top,viewportEnd) - main.getBoundingClientRect().top - 8));
      const value = height + 'px';
      if (d.documentElement.style.getPropertyValue('--pw-content-max-height') !== value)
        d.documentElement.style.setProperty('--pw-content-max-height', value);
    });
  }
  w.addEventListener('resize',scheduleLayout);
  if (w.visualViewport) w.visualViewport.addEventListener('resize',scheduleLayout);

  function refresh() {
    scheduleLayout();
    d.documentElement.dataset.pwReducedMotion = String(reduced());
    for (const button of d.querySelectorAll('[data-pw-motion]')) {
      const label = preference.matches ? button.dataset.system : (reduced() ? button.dataset.enable : button.dataset.reduce);
      if (button.textContent !== label) button.textContent = label;
      button.disabled = preference.matches;
    }
    const process = d.querySelector('.fan-process');
    if (process && process.children.length === 3 && !seenMethod) {
      seenMethod = true;
      if (!reduced()) for (const [index,step] of [...process.children].entries()) {
        step.animate([{transform:'translateY(6px)'},{transform:'translateY(0)'}],
          {duration:220,delay:index*45,easing:'ease-out'});
      }
    }
    if (reduced()) for (const node of d.querySelectorAll('.fan-process-step')) {
      for (const animation of node.getAnimations()) animation.cancel();
    }
  }
  d.addEventListener('click', event => {
    const button = event.target.closest('[data-pw-motion]');
    if (button) {
      disabled = !disabled;
      try { w.sessionStorage.setItem('pitwall-motion-disabled',String(disabled)); } catch (_) {}
      refresh(); return;
    }
    const link = event.target.closest('a[data-pw-scroll],a.pw-skip-link');
    if (!link || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const target = d.getElementById(link.getAttribute('href').slice(1));
    if (!target) return;
    event.preventDefault();
    target.focus({preventScroll:true});
    target.scrollIntoView({behavior:reduced()?'instant':'smooth',block:'start'});
  });
  // Only inspect element insertions: our attribute/text updates cannot loop.
  const observer = new w.MutationObserver(records => {
    if (records.some(r=>[...r.addedNodes].some(n=>n.nodeType===1))) refresh();
  });
  observer.observe(d.body,{childList:true,subtree:true});
  preference.addEventListener('change',refresh);
  w.__pitwallMotion = {refresh};
  refresh();
})();
