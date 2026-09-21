import { Bath, BedDouble, BriefcaseBusiness, Ruler } from 'lucide-react';
import { money, plural, slug } from '@/data/siteData';

export const UnitFacts = ({ unit, prefix }) => <div className="mt-5 flex flex-wrap gap-4 border-y border-stone-200 py-4 text-sm font-semibold text-stone-700" data-testid={`${prefix}-facts`}>
  {unit.use === 'Residential' ? <><span className="inline-flex items-center gap-2"><BedDouble className="h-4 w-4 text-copper" />{plural(unit.beds, 'bed')}</span><span className="inline-flex items-center gap-2"><Bath className="h-4 w-4 text-copper" />{plural(unit.baths, 'bath')}</span></> : <span className="inline-flex items-center gap-2"><BriefcaseBusiness className="h-4 w-4 text-copper" />{unit.commercial.intended_use}</span>}
  <span className="inline-flex items-center gap-2"><Ruler className="h-4 w-4 text-copper" />{unit.sqft.toLocaleString()} sq ft</span>
</div>;

export const UnitTerms = ({ unit, compact = false, prefix }) => {
  const terms = unit.use === 'Residential' ? [
    ['Monthly rent', money(unit.rent, unit.currency)], ['Security deposit', money(unit.deposit, unit.currency)], ['Application fee', unit.applicationFee], ['Availability', unit.available_date || 'Occupied example'], ['Utilities', unit.utilities], ['Pet policy', unit.petPolicy],
  ] : [
    ['Base rent', `${money(unit.rent, unit.currency)} / ${unit.commercial.rent_period}`], ['Deposit', money(unit.deposit, unit.currency)], ['Lease type', unit.commercial.lease_type], ['CAM / NNN', unit.commercial.cam_nnn_terms], ['Utility responsibility', unit.commercial.utility_responsibility], ['Zoning / use notes', unit.commercial.zoning_notes], ['Loading / access', unit.commercial.loading_access], ['Parking', unit.commercial.parking], ['Build-out status', unit.commercial.build_out_status], ['Available date', unit.available_date || 'Occupied example'],
  ];
  return <dl className={`mt-5 grid gap-4 text-sm ${compact ? 'sm:grid-cols-2' : ''}`}>
    {(compact ? terms.slice(1, 3) : terms).map(([label, value]) => <div key={label} data-testid={`${prefix}-${slug(label)}`}><dt className="text-stone-600">{label}</dt><dd className="mt-1 font-semibold leading-6">{value}</dd></div>)}
  </dl>;
};