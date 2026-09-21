import foundation from './generated/foundation.json';
import { PHASE0 } from '@/config/phase0';

export const DEMO_NOTICE = 'Seeded demonstration data · not verified availability';
export const FOUNDATION = foundation;
export const IMAGES = {
  hero: 'https://images.unsplash.com/photo-1709755813430-5dbd547214df?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85',
  skyline: 'https://images.pexels.com/photos/33303158/pexels-photo-33303158.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1440',
  mixedUse: 'https://images.unsplash.com/photo-1691902588772-c93ed83b7f38?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85',
  duplex: 'https://images.unsplash.com/photo-1646909458037-41fc0f106cb5?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85',
  triplex: 'https://images.pexels.com/photos/28949071/pexels-photo-28949071.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1200',
  bakery: 'https://images.unsplash.com/photo-1511018556340-d16986a1c194?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85',
  storefront: 'https://images.unsplash.com/photo-1601205741712-b261aff33a7d?crop=entropy&cs=srgb&fm=jpg&ixlib=rb-4.1.0&q=85',
};

export const HEADLINES = [
  { tag: 'Homes & spaces', title: 'A better place to rent. A clearer way to live.', subtitle: 'Residential, commercial, and mixed-use spaces. A considered approach to property care, beginning in Greater Cincinnati.' },
  { tag: 'Resident care', title: 'A thoughtful home. A connected community.', subtitle: 'Clear terms, individual identities, and a more considered resident experience. Connected by PerchPoint.' },
  { tag: 'Property operations', title: 'Local stewardship, down to every unit.', subtitle: 'HawkVision Homes brings houses, multifamily buildings, and commercial spaces into one property-operations vision.' },
];

export const PORTFOLIO = foundation.portfolio;
export const money = (amount, currency = 'USD') => new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount);
export const plural = (count, noun) => `${count} ${noun}${count === 1 ? '' : 's'}`;
export const slug = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const displayUnit = (unit) => {
  const property = PORTFOLIO.properties.find((p) => p.id === unit.property_id);
  const residential = unit.residential;
  const commercial = unit.commercial;
  return {
    ...unit, propertyId: property.id, buildingId: unit.building_id, propertyName: property.name,
    title: `${property.name} · ${unit.label}`, unit: unit.label,
    address: property.address.line1,
    neighborhood: `${property.address.municipality}, ${property.address.state}`,
    type: property.property_type.replaceAll('_', '-').replace(/^./, (s) => s.toUpperCase()),
    use: unit.use === 'commercial' ? 'Commercial' : 'Residential',
    rent: (residential?.monthly_rent || commercial.base_rent).amount_minor / 100,
    deposit: (residential?.security_deposit || commercial.deposit).amount_minor / 100,
    currency: (residential?.monthly_rent || commercial.base_rent).currency,
    beds: residential?.bedrooms, baths: residential?.bathrooms, sqft: unit.square_feet,
    available: `Example: ${unit.status === 'available' ? 'available' : 'occupied'}`,
    image: IMAGES[unit.image_key],
    utilities: residential?.utilities || commercial.utility_responsibility,
    petPolicy: residential?.pet_policy,
    applicationFee: residential ? `${money(residential.application_fee.amount_minor / 100)} per adult · example` : undefined,
    note: commercial ? commercial.intended_use + ' — synthetic commercial terms; use and permits are not verified.' : 'An illustrative residential unit with its own household, lease, utilities and maintenance context.',
  };
};
export const ALL_UNITS = PHASE0.seedsEnabled ? PORTFOLIO.units.map(displayUnit) : [];
export const RENTALS = PHASE0.seedsEnabled ? PORTFOLIO.properties.flatMap((p) => ALL_UNITS.filter((u) => u.propertyId === p.id).slice(0, 1)) : [];
export const BAKERY = ALL_UNITS.find((u) => u.unit === 'Bakery C1');

export const ROLE_ACCOUNTS = [
  { id: 'owner', name: 'Farouk', role: 'Owner / Asset Principal', scope: 'Business and operational oversight. Infrastructure, secrets, deployment and audit deletion are excluded.' },
  { id: 'super-admin', name: 'Nathan', role: 'Platform Super Administrator', scope: 'Technical administration is distinct from business actions, development and emergency support. No impersonation is available.' },
  { id: 'leasing', name: 'Leasing Preview', role: 'Leasing / Project Manager', scope: 'Portfolio-wide operations. No unrestricted screening, privileged financial adjustments or owner-reserved decisions.' },
  { id: 'accounting', name: 'Accounting Preview', role: 'Accounting Contractor', scope: 'Authorized financial records, reconciliation, reports and approved documents only.' },
  { id: 'maintenance', name: 'Maintenance Preview', role: 'Maintenance Employee', scope: 'Assigned work and the minimum property, access, scheduling and coordination context.' },
  { id: 'subcontractor', name: 'Subcontractor Preview', role: 'Subcontractor', scope: 'One synthetic assignment only. No broad tenant, applicant, financial or portfolio access.' },
  { id: 'resident', name: 'Household Preview', role: 'Primary Resident', scope: 'Own household records only. Adult signers retain separate individual identities.' },
  { id: 'applicant', name: 'Applicant Preview', role: 'Applicant', scope: 'Own application relationships and allowed disclosures only. No screening has been ordered.' },
];