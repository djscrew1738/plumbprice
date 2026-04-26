/**
 * Register the PlumbPrice service worker.
 *
 * On update, fires a custom 'sw-update-available' window event so a banner
 * component can prompt the user to refresh. Pass `applyUpdate()` to the
 * banner's "Reload" handler to activate the new SW immediately.
 */
export function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

  window.addEventListener('load', async () => {
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
  });
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
