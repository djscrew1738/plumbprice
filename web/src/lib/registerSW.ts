/**
 * Register the PlumbPrice service worker.
 *
 * Registration is deferred by 3 seconds after the page loads to avoid
 * competing with user interactions (typing, button clicks) during the
 * critical first-interaction window — especially important on iOS where
 * SW install can briefly saturate the JS thread.
 *
 * On update, fires a custom 'sw-update-available' window event so a banner
 * component can prompt the user to refresh. Pass `applyUpdate()` to the
 * banner's "Reload" handler to activate the new SW immediately.
 */
export function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

  const register = async () => {
    try {
      const reg = await navigator.serviceWorker.register('/sw.js');

      // If a new SW is waiting (user has tabs open across releases), surface it.
      if (reg.waiting) notifyUpdate(reg);

      reg.addEventListener('updatefound', () => {
        const installing = reg.installing;
        if (!installing) return;
        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed' && navigator.serviceWorker.controller) {
            notifyUpdate(reg);
          }
        });
      });

      // Reload the page once the new SW takes control (one-shot listener).
      let refreshing = false;
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (refreshing) return;
        refreshing = true;
        window.location.reload();
      });
    } catch {
      // Registration failures are non-fatal — the app still works online.
    }
  };

  // Defer registration until the page has been idle for at least 3 seconds.
  // This prevents SW install from competing with first keystrokes on mobile.
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(() => setTimeout(register, 1000), { timeout: 5000 });
  } else {
    setTimeout(register, 3000);
  }
}

function notifyUpdate(reg: ServiceWorkerRegistration) {
  window.dispatchEvent(
    new CustomEvent('sw-update-available', {
      detail: {
        applyUpdate: () => {
          if (reg.waiting) reg.waiting.postMessage('SKIP_WAITING');
        },
      },
    }),
  );
}
