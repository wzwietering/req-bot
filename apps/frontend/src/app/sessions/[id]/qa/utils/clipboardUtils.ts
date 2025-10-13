/**
 * Fallback copy method for browsers without Clipboard API.
 * Uses deprecated execCommand as last resort.
 */
function fallbackCopyToClipboard(text: string): Promise<void> {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-999999px';

  document.body.appendChild(textArea);
  textArea.select();

  try {
    document.execCommand('copy');
    return Promise.resolve();
  } catch (err) {
    return Promise.reject(err);
  } finally {
    document.body.removeChild(textArea);
  }
}

function hasClipboardAPI(): boolean {
  return !!navigator.clipboard?.writeText;
}

export function copyToClipboard(text: string): Promise<void> {
  if (hasClipboardAPI()) {
    return navigator.clipboard.writeText(text);
  }

  return fallbackCopyToClipboard(text);
}
