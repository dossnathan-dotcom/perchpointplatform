import { FOUNDATION, PORTFOLIO, slug } from './siteData';

export const PORTAL_VIEWS = {
  owner: { label: 'Owner Command Center', tabs: ['Portfolio', 'Reserved approvals', 'Financial oversight', 'Delegations', 'Business audit'] },
  'super-admin': { label: 'Platform Administration', tabs: ['System overview', 'Identity contracts', 'Permission matrix', 'Provider registry', 'Audit and events', 'Technical boundaries'] },
  leasing: { label: 'Leasing Operations', tabs: ['Operations Console', 'Operational inbox', 'Leasing pipeline', 'Showing queue', 'Application queue', 'Tenant directory', 'Maintenance coordination', 'Payment exceptions', 'Approval requests', 'Documents and expirations', 'Tasks', 'Communication activity', 'System exceptions'] },
  accounting: { label: 'Accounting', tabs: ['Reconciliation', 'Ledger preview', 'Payment exceptions', 'Approved documents', 'Reporting'] },
  maintenance: { label: 'Maintenance Operations', tabs: ['Assigned work', 'Schedule', 'Parts and estimates', 'Completion evidence'] },
  subcontractor: { label: 'Subcontractor Assignments', tabs: ['My assignment', 'Site access', 'Estimate', 'Evidence', 'Invoice'] },
  resident: { label: 'Resident Portal', tabs: ['Household', 'Balance and charges', 'Lease and documents', 'Maintenance', 'Communications', 'Preferences'] },
  applicant: { label: 'Applicant Portal', tabs: ['Application status', 'Household applicants', 'Document requests', 'Consent and screening', 'Showing history', 'Next steps'] },
};

const elm = PORTFOLIO.properties[0];
const record = (id, title, detail, status='Planned', propertyId=elm.id) => ({ id, title, detail, status, propertyId });
export const ASSIGNMENT = record('hvac-example', 'Example rooftop HVAC inspection', 'One assigned job · Example Elm Court · Building 1', 'Seeded assignment');

export function previewRecords(role, tab) {
  const key = slug(tab);
  if (role === 'subcontractor') return [record(`vendor-${key}`, tab === 'My assignment' ? ASSIGNMENT.title : `${tab} · HVAC assignment`, tab === 'Site access' ? 'Assigned building only. Real entry codes and resident contact details are not included.' : 'Synthetic assignment reference; no estimate, upload or invoice is submitted.', 'Seeded assignment')];
  if (role === 'maintenance') return [ASSIGNMENT, record(`maintenance-${key}`, `${tab} · protective action`, 'Emergency example requires immediate notification and retrospective review; no dispatch occurs.', 'Emergency example')];
  if (role === 'resident') return tab === 'Household' ? FOUNDATION.people.relationships.filter((r) => r.household_id === FOUNDATION.people.households[0].id).map((r) => record(r.id, FOUNDATION.people.people.find((p) => p.id === r.person_id).display_name, `${r.kind.replaceAll('_',' ')} · ${r.account_id ? 'individual synthetic account reference' : 'no portal account'}`, 'Synthetic relationship')) : [record(`resident-${key}`, tab, tab === 'Balance and charges' ? 'No live balance, payment method or financial posting exists.' : 'Household-scoped future record. No real document, notice or communication.', 'Not connected')];
  if (role === 'applicant') return tab === 'Household applicants' ? FOUNDATION.people.relationships.filter((r) => r.household_id === FOUNDATION.people.households[1].id).map((r) => record(r.id, FOUNDATION.people.people.find((p) => p.id === r.person_id).display_name, `${r.kind.replaceAll('_',' ')} · separate identity`, 'Synthetic relationship')) : [record(`applicant-${key}`, tab, 'No application submission, screening order, consent, ranking or decision has been made.', 'Not started')];
  if (role === 'super-admin') {
    if (tab === 'Provider registry') return FOUNDATION.integrations.map((i) => record(i.id, i.provider_type.replaceAll('_',' '), i.provider_name, 'Disconnected', null));
    if (tab === 'Identity contracts') return FOUNDATION.identity.map((i) => record(i.operation, i.operation.replaceAll('_',' '), i.preconditions.join(' · '), 'Contract only', null));
    return [record(`admin-${key}`, tab, 'Technical authority is a contract only. No live environment, permission or security controls are exposed.', 'Contract only', null)];
  }
  if (role === 'owner' && tab === 'Portfolio') return PORTFOLIO.properties.map((p) => record(p.id, p.name, `${p.property_type.replaceAll('_',' ')} · ${p.address.municipality}, ${p.address.state}`, 'Fictional property', p.id));
  if (role === 'owner' && tab === 'Delegations') return FOUNDATION.scenarios.slice(0,4).map((s,i) => record(`delegation-${i}`, s.name, s.detail.reasons.join(' · '), s.actual));
  if (role === 'owner' && tab === 'Reserved approvals') return ['New lease', 'Final applicant decision', 'Legal matters'].map((title,i) => record(`reserved-${i}`,title,'Reserved for Farouk. No live approval or rejection action.', 'Owner reserved'));
  if (role === 'accounting') return [record(`accounting-${key}`, tab, 'Authorized financial records only. No real balances, transactions, exports or adjustments.', 'Not connected')];
  if (role === 'leasing') {
    const messages = {'Operational inbox':'Showing interest · synthetic queue', 'Leasing pipeline':'Example Elm Court · Unit 1A', 'Showing queue':'No real appointment has been scheduled', 'Application queue':'Two individual adult applicants · synthetic household', 'Tenant directory':'Primary holder and adult co-signer · synthetic identities', 'Maintenance coordination':ASSIGNMENT.title, 'Payment exceptions':'Payment provider is disconnected', 'Approval requests':'Final applicant and new lease decisions reserved for Farouk', 'Documents and expirations':'No documents uploaded; legal retention periods pending review', 'Tasks':'Confirm ownership entities and jurisdiction policies', 'Communication activity':'No email or SMS is sent from this preview', 'System exceptions':'Screening and payment adapters disconnected'};
    return tab === 'Operations Console' ? Object.entries(messages).map(([title,detail]) => record(slug(title),title,detail, title.includes('exceptions') ? 'Disconnected' : 'Seeded preview')) : [record(`leasing-${key}`,tab,messages[tab] || 'Contract-only queue','Seeded preview')];
  }
  return [record(`${role}-${key}`,tab,'No live operational records or actions in this workspace.','Contract only')];
}

export const DELEGATION_RULES = [
  ['Routine purchase', 'Within approved budget + configured staff limit', 'Independent delegated approver', 'No self-approval'],
  ['Parts above example $500', 'Configurable seeded threshold', 'Manager or owner', 'Cumulative issue total'],
  ['Repair above monthly rent', 'Configured rent multiplier', 'Farouk', 'Reserved approval'],
  ['Outside approved budget', 'Unknown or exceeded budget', 'Farouk', 'Variance review'],
  ['Lease / final applicant / legal', 'Owner-reserved decision types', 'Farouk', 'Reason and audit'],
  ['Life/property emergency', 'Necessary protective action + evidence', 'In-scope emergency authority', 'Immediate notification + retrospective review'],
];