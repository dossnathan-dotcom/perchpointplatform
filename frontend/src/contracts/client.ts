import { z } from 'zod';
import type { Portfolio, Unit } from './generated';

const summarySchema = z.object({
  version: z.string(),
  data_status: z.literal('synthetic_contracts_only'),
  production_authentication: z.literal(false),
  provider_execution: z.literal(false),
  canonical_persistence: z.literal(false),
}).strict();

export async function getFoundationStatus() {
  const base = process.env.REACT_APP_BACKEND_URL;
  if (!base) throw new Error('REACT_APP_BACKEND_URL is required');
  const response = await fetch(`${base}/api/foundation`);
  if (!response.ok) throw new Error('Foundation metadata unavailable');
  return summarySchema.parse(await response.json());
}

// Generated domain types are used at the frontend boundary; they confer no authorization.
export function unitsForProperty(portfolio: Portfolio, propertyId: string): Unit[] {
  return portfolio.units.filter((unit) => unit.property_id === propertyId);
}