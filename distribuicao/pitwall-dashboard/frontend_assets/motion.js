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
