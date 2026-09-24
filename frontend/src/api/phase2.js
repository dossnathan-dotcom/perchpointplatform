export async function phase2(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  return { response, body };
}

export function moneyMinor(amount, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format((amount || 0) / 100);
}
