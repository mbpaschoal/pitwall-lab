/* Sidebar/card bridge also installs beside the pre-0.13 motion singleton. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallEditorial) { w.__pitwallEditorial.refresh(); return; }
  const preference = w.matchMedia('(prefers-reduced-motion: reduce)');
  const reduced = () => {
    if (preference.matches || d.documentElement.dataset.pwReducedMotion === 'true') return true;
    try { return w.sessionStorage.getItem('pitwall-motion-disabled') === 'true'; }
    catch (_) { return false; }
  };
  const deckMemory = new Map();
  const cardMotion = new Set();
  let opening = null, openingTimer = 0, activeDeck = null, returnFocusKey = null;

  function clearCardOpening() {
    opening = null;
    w.clearTimeout(openingTimer);
    delete d.documentElement.dataset.pwCardOpening;
  }

  function cancelCardMotion() {
    for (const animation of cardMotion) animation.cancel();
    cardMotion.clear();
  }

  function playCardMotion(node, frames, duration) {
    if (reduced() || !node.isConnected || typeof node.animate !== 'function') return;
    for (const animation of cardMotion) {
      if (animation.effect?.target === node) animation.cancel();
    }
    const animation = node.animate(frames, {duration, easing:'cubic-bezier(.16,1,.3,1)'});
    cardMotion.add(animation);
    animation.onfinish = animation.oncancel = () => cardMotion.delete(animation);
  }

  function focusCardDialog(dialog) {
    const modal = dialog.closest('[data-testid="stDialog"]') || dialog;
    if (modal.contains(d.activeElement)) return;
    dialog.tabIndex = -1;
    dialog.focus({preventScroll:true});
  }

  function syncCardDialog(deck) {
    if (activeDeck === deck) return;
    cancelCardMotion();
    returnFocusKey = deck ? null : activeDeck.dataset.deckKey;
    activeDeck = deck;
    if (!deck) {
      clearCardOpening();
      return;
    }
    const origin = opening;
    const dialog = deck.closest('[role="dialog"]');
    const panel = dialog.parentElement.parentElement?.dataset.testid === 'stDialog'
      ? dialog.parentElement : dialog;
    // Capture the settled native panel after the card payload mounts.
    w.requestAnimationFrame(() => {
      if (!panel.isConnected || activeDeck !== deck) return;
      if (!reduced() && origin && opening === origin && origin.key === deck.dataset.deckKey) {
        const end = panel.getBoundingClientRect();
        if (end.width && end.height) {
          const x = origin.rect.x - end.x, y = origin.rect.y - end.y;
          const width = origin.rect.width / end.width, height = origin.rect.height / end.height;
          playCardMotion(panel, [
            {transformOrigin:'top left', transform:`translate(${x}px,${y}px) scale(${width},${height})`, borderRadius:'6px'},
            {transformOrigin:'top left', transform:'none', borderRadius:'12px'}
          ], 360);
        }
      }
      clearCardOpening();
      focusCardDialog(dialog);
    });
  }

  function restoreCardFocus() {
    if (!returnFocusKey || new URLSearchParams(w.location.search).has('cartas') ||
        app?.dataset.testScriptState !== 'notRunning') return;
    const context = d.querySelector('[data-pw-deck-context]');
    const focusLost = d.activeElement === d.body || d.activeElement?.matches('main.stMain');
    if (context?.dataset.pwDeckContext === returnFocusKey && focusLost) {
      d.querySelector('.st-key-open_tarot button')?.focus({preventScroll:true});
    }
    returnFocusKey = null;
  }
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
      // Streamlit may reuse the card node while replacing HTML descendants.
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
        if (animate && index === focusIndex) {
          const face = shown ? slot : card.querySelector('[data-tarot-reveal]');
          const direction = shown ? -1 : 1;
          playCardMotion(face, [
            {transform:`rotateY(${direction * 72}deg) scale(.97)`},
            {transform:`rotateY(${-direction * 3}deg)`, offset:.75},
            {transform:'none'}
          ], 330);
        }
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
    const deck = d.querySelector('[role="dialog"] .pw-tarot-reading');
    if (deck) refreshDeck(deck);
    syncCardDialog(deck);
    if (!deck) restoreCardFocus();
    else if (!opening && app?.dataset.testScriptState === 'notRunning') {
      focusCardDialog(deck.closest('[role="dialog"]'));
    }
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
    const trigger = event.target.closest('.st-key-open_tarot button');
    const context = trigger && d.querySelector('[data-pw-deck-context]');
    if (!context) return;
    // Some touch browsers do not focus a pressed button before opening a dialog.
    trigger.focus({preventScroll:true});
    if (reduced() || typeof trigger.animate !== 'function') return;
    clearCardOpening();
    opening = {key:context.dataset.pwDeckContext, rect:trigger.getBoundingClientRect()};
    // Wait for the real deck rather than showing the empty native shell first.
    d.documentElement.dataset.pwCardOpening = 'true';
    openingTimer = w.setTimeout(clearCardOpening, 1800);
  }, true);
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
  d.addEventListener('focusout', event => {
    const dialog = activeDeck?.closest('[role="dialog"]');
    const modal = dialog?.closest('[data-testid="stDialog"]');
    if (!modal?.contains(event.target) || modal.contains(event.relatedTarget)) return;
    // Native focus can briefly fall back to the page during a Streamlit rerender.
    w.requestAnimationFrame(() => {
      if (dialog.isConnected && dialog.contains(activeDeck) && !opening &&
          new URLSearchParams(w.location.search).has('cartas')) focusCardDialog(dialog);
    });
  }, true);
  new w.MutationObserver(records => {
    if (records.some(r => [...r.addedNodes,...r.removedNodes].some(n => n.nodeType === 1))) refresh();
  }).observe(d.body,{childList:true,subtree:true});
  const app = d.querySelector('.stApp');
  if (app) new w.MutationObserver(refresh).observe(app,{attributes:true,attributeFilter:['data-test-script-state']});
  function stopReducedMotion() {
    if (!reduced()) return;
    clearCardOpening();
    cancelCardMotion();
  }
  preference.addEventListener('change', stopReducedMotion);
  new w.MutationObserver(stopReducedMotion).observe(d.documentElement, {
    attributes:true, attributeFilter:['data-pw-reduced-motion']
  });
  w.addEventListener('pagehide', cancelCardMotion);
  w.addEventListener('resize',refresh);
  w.__pitwallEditorial = {refresh, readDeckState:savedDeckState};
  refresh();
})();

/* Shell behavior installs independently in tabs that loaded an earlier bridge. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallShell) { w.__pitwallShell.refresh(); return; }
  const menuSelector = '.st-key-pw-sidebar-menu details';
  let observedHeader = null, pending = false;

  function settleMenu(menu) {
    if (!menu?.matches(menuSelector)) return;
    // Streamlit animates the expander's height for 500 ms. A clipped menu can
    // scroll between pointerdown and pointerup and cancel a native button click.
    for (const animation of menu.getAnimations())
      if (animation.playState !== 'finished' && animation.playState !== 'idle') animation.finish();
  }

  function refresh() {
    pending = false;
    const header = d.querySelector('.st-key-journey-header')?.parentElement;
    if (header !== observedHeader) {
      if (observedHeader) resize.unobserve(observedHeader);
      if (header) resize.observe(header);
      observedHeader = header;
    }
    if (header) {
      const height = Math.ceil(header.getBoundingClientRect().height) + 'px';
      if (d.documentElement.style.getPropertyValue('--pw-header-height') !== height)
        d.documentElement.style.setProperty('--pw-header-height', height);
    }
    const navigation = d.querySelector('.st-key-pw-sidebar-menu');
    if (navigation) {
      navigation.setAttribute('role', 'navigation');
      navigation.setAttribute('aria-label', d.documentElement.lang === 'en' ? 'Explore Pitwall' : 'Explorar o Pitwall');
    }
    settleMenu(d.querySelector(menuSelector));
  }

  function schedule() {
    if (!pending) { pending = true; w.requestAnimationFrame(refresh); }
  }
  const resize = new w.ResizeObserver(schedule);
  d.addEventListener('toggle', event => settleMenu(event.target), true);
  d.addEventListener('click', event => {
    const summary = event.target.closest('.st-key-pw-sidebar-menu summary');
    if (summary) settleMenu(summary.closest('details'));
  });
  new w.MutationObserver(records => {
    if (records.some(record => [...record.addedNodes, ...record.removedNodes].some(node => node.nodeType === 1))) schedule();
  }).observe(d.body, {childList: true, subtree: true});
  new w.MutationObserver(schedule).observe(d.documentElement, {attributes: true, attributeFilter: ['lang']});
  w.__pitwallShell = {refresh};
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
