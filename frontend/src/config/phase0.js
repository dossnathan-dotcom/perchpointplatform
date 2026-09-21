export function phase0Flags(env) {
  const flag = (name) => {
    if (!['true', 'false'].includes(env[name])) throw new Error(`${name} must be explicitly true or false`);
    return env[name] === 'true';
  };
  const showLabels = flag('REACT_APP_SHOW_DEMO_LABELS');
  // Never publish unlabeled synthetic inventory: hiding labels also hides seeded surfaces.
  const requested = flag('REACT_APP_ENABLE_SEEDED_PREVIEWS');
  return { showLabels, seedsEnabled: requested && showLabels };
}

export const PHASE0 = phase0Flags({
  REACT_APP_SHOW_DEMO_LABELS: process.env.REACT_APP_SHOW_DEMO_LABELS,
  REACT_APP_ENABLE_SEEDED_PREVIEWS: process.env.REACT_APP_ENABLE_SEEDED_PREVIEWS,
});