/* Local adaptation of motion principles; no upstream engine or external calls. */
(() => {
  const w = window.parent, d = w.document;
  if (w.__pitwallMotion) { w.__pitwallMotion.refresh(); return; }
  const preference = w.matchMedia('(prefers-reduced-motion: reduce)');
  let disabled = false, seenMethod = false;
  try { disabled = w.sessionStorage.getItem('pitwall-motion-disabled') === 'true'; } catch (_) {}
  const reduced = () => disabled || preference.matches;
  function refresh() {
    d.documentElement.dataset.pwReducedMotion = String(reduced());
    for (const button of d.querySelectorAll('[data-pw-motion]')) {
      const label = preference.matches ? button.dataset.system : (reduced() ? button.dataset.enable : button.dataset.reduce);
      if (button.textContent !== label) button.textContent = label;
      button.setAttribute('aria-pressed', String(reduced()));
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
