/**
 * Promise-shaped wrapper around navigator.geolocation with a hard timeout
 * and graceful error reporting. Used by the photo capture flow to attach
 * jobsite GPS coordinates to a Photo row when the user opts in.
 */

export interface GeoFix {
  lat: number;
  lng: number;
  accuracy: number;
}

export async function getGeolocation(timeoutMs = 8000): Promise<GeoFix> {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    throw new Error('Geolocation is not supported in this browser.');
  }
  return new Promise<GeoFix>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Location timed out')), timeoutMs);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        clearTimeout(timer);
        resolve({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => {
        clearTimeout(timer);
        // PERMISSION_DENIED, POSITION_UNAVAILABLE, TIMEOUT
        reject(new Error(err.message || 'Location unavailable'));
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60_000 }
    );
  });
}
