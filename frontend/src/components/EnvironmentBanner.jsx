export function EnvironmentBanner() {
  const environment = process.env.REACT_APP_PHASE3_ENVIRONMENT || "local";
  if (environment === "production") return null;
  return <p className="bg-copper px-4 py-2 text-center text-sm text-white" data-testid="environment-indicator">Nonproduction environment: {environment}. This is not the live HawkVision site.</p>;
}
