import { phase0Flags } from './phase0';

describe('phase0Flags', () => {
  test('returns seeds disabled when labels disabled', () => {
    const flags = phase0Flags({
      REACT_APP_SHOW_DEMO_LABELS: 'false',
      REACT_APP_ENABLE_SEEDED_PREVIEWS: 'true',
    });
    expect(flags).toEqual({ showLabels: false, seedsEnabled: false });
  });

  test('throws when flag values are not explicit true/false', () => {
    expect(() =>
      phase0Flags({
        REACT_APP_SHOW_DEMO_LABELS: '1',
        REACT_APP_ENABLE_SEEDED_PREVIEWS: 'true',
      })
    ).toThrow(/must be explicitly true or false/);
  });
});