import { AlertTriangle, Inbox, LoaderCircle, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';

export const PreviewState = ({ state, onReset }) => {
  const views = { empty: [Inbox, 'Nothing in this queue', 'No synthetic records match the current selection.'], loading: [LoaderCircle, 'Loading preview', 'Simulated loading state. No provider request is running.'], error: [AlertTriangle, 'Preview unavailable', 'Simulated connection error. No changes were saved.'], denied: [Shield, 'Access not granted', 'Sensitive records are denied in this preview. This is not production authorization.'] };
  const [Icon,title,copy] = views[state];
  return <div className="border-y border-white/20 py-16 text-center" role="status" data-testid={`portal-state-${state}`}><Icon className={`mx-auto h-7 w-7 text-gold ${state === 'loading' ? 'animate-spin' : ''}`} /><h2 className="mt-5 font-heading text-2xl">{title}</h2><p className="mx-auto mt-3 max-w-lg px-4 text-sm leading-7 text-linen/75">{copy}</p><Button className="mt-6 border border-white/50 bg-transparent text-linen hover:bg-white/10" onClick={onReset} data-testid="portal-state-reset-btn">{state === 'error' ? 'Retry preview' : 'Return to seeded view'}</Button></div>;
};