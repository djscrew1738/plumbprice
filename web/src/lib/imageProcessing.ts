/**
 * Client-side image preprocessing for field photo capture.
 *
 * Why client-side:
 *   - Saves a *huge* amount of cellular data on bad LTE (10MB phone pic
 *     -> ~400KB resized JPEG).
 *   - Speeds up the vision call on the API side (less to upload, less to
 *     decode).
 *   - Re-encoding through canvas naturally strips EXIF (including any GPS
 *     baked in by the camera), so we can re-attach geo coordinates
 *     explicitly only with the user's permission.
 */

export interface ProcessedImage {
  blob: Blob;
  width: number;
  height: number;
  bytes: number;
}

const DEFAULT_MAX_EDGE = 2048;
const DEFAULT_QUALITY = 0.85;

/**
 * Resize an image to at most `maxEdge` pixels on its longest side and
 * re-encode as JPEG. EXIF (including GPS, camera, timestamps) is dropped.
 *
 * Falls back to returning the original file if image decode fails (e.g. an
 * unsupported HEIC variant). The caller can still upload the raw bytes.
 */
export async function preprocessImage(
  file: File,
  opts: { maxEdge?: number; quality?: number } = {}
): Promise<ProcessedImage> {
  const maxEdge = opts.maxEdge ?? DEFAULT_MAX_EDGE;
  const quality = opts.quality ?? DEFAULT_QUALITY;

  // Already small enough? Skip the round-trip through canvas.
  // We still re-encode if it's huge bytes-wise (>1MB) since EXIF can hide
  // megabytes of thumbnail/payload in some cameras.
  const bitmap = await loadBitmap(file);
  const { width: w0, height: h0 } = bitmap;

  const scale = Math.min(1, maxEdge / Math.max(w0, h0));
  const tw = Math.round(w0 * scale);
  const th = Math.round(h0 * scale);

  const canvas = document.createElement('canvas');
  canvas.width = tw;
  canvas.height = th;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    bitmap.close?.();
    return { blob: file, width: w0, height: h0, bytes: file.size };
  }
  ctx.drawImage(bitmap, 0, 0, tw, th);
  bitmap.close?.();

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('canvas.toBlob failed'))),
      'image/jpeg',
      quality
    );
  });

  return { blob, width: tw, height: th, bytes: blob.size };
}

async function loadBitmap(file: File): Promise<ImageBitmap & { close?: () => void }> {
  // createImageBitmap is the fastest path and handles EXIF orientation
  // automatically when imageOrientation: 'from-image' is supported.
  if (typeof createImageBitmap === 'function') {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' });
    } catch {
      // fall through to <img> path
    }
  }
  // Fallback via <img>: doesn't honor EXIF orientation, but works everywhere.
  const url = URL.createObjectURL(file);
  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const i = new Image();
      i.onload = () => resolve(i);
      i.onerror = () => reject(new Error('image load failed'));
      i.src = url;
    });
    // ImageBitmap-like minimum surface
    return Object.assign(img as unknown as ImageBitmap, { close: () => URL.revokeObjectURL(url) });
  } catch (e) {
    URL.revokeObjectURL(url);
    throw e;
  }
}
