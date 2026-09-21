import { PHASE0 } from '@/config/phase0';

export const DemoNotice = ({ id, children = 'Seeded demonstration data · not verified availability', className = '' }) => (
  PHASE0.showLabels ? <p className={`demo-notice ${className}`} data-testid={id}>{children}</p> : null
);