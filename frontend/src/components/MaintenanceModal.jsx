import { useState } from 'react';
import axios from 'axios';
import { Loader2, Wrench } from 'lucide-react';
import { PHASE0 } from '@/config/phase0';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const initial = {name:'',email:'',property_address:'',unit:'',category:'Plumbing',description:'',permission_to_enter:false};
export const MaintenanceModal = ({open,onOpenChange}) => {
  const [form,setForm] = useState(initial);
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState('');
  const [confirmation,setConfirmation] = useState('');
  const field = (key,value) => setForm({...form,[key]:value});
  const submit = async (event) => {
    event.preventDefault();setLoading(true);setError('');setConfirmation('');
    try { const {data}=await axios.post(`${API}/maintenance-requests`,form);setConfirmation(`${data.id}: ${data.message}`);setForm(initial); }
    catch (err) {setError(typeof err.response?.data?.detail==='string'?err.response.data.detail:'Please complete the required maintenance details.');}
    finally {setLoading(false);}
  };
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="max-h-[90dvh] max-w-xl overflow-y-auto border-stone-200 bg-linen p-7 text-obsidian" data-testid="maintenance-request-dialog"><Wrench className="h-7 w-7 text-copper" /><DialogHeader><DialogTitle className="font-heading text-3xl">Maintenance request preview</DialogTitle><DialogDescription data-testid="maintenance-safety-warning">For immediate danger, leave the area and call your local emergency number (911 in the US). This synthetic form does not dispatch help. Use fictional details and an example.com email.</DialogDescription></DialogHeader>
    <form onSubmit={submit} className="grid gap-4"><div className="grid gap-4 sm:grid-cols-2">{[['name','Example name','text',2],['email','Example email','email',3],['property_address','Example address','text',5],['unit','Unit','text',1]].map(([key,label,type,min]) => <label htmlFor={`maintenance-${key}`} key={key} className="grid gap-2 text-sm font-semibold">{label}<Input id={`maintenance-${key}`} type={type} required minLength={min} value={form[key]} onChange={(e) => field(key,e.target.value)} data-testid={`maintenance-${key==='property_address'?'address':key}-input`} /></label>)}</div>
      <label htmlFor="maintenance-category" className="grid gap-2 text-sm font-semibold">Category<select id="maintenance-category" className="h-11 border border-stone-500 bg-white px-3" value={form.category} onChange={(e) => field('category',e.target.value)} data-testid="maintenance-category-select">{['Plumbing','Electrical','Heating / cooling','Appliance','Access / security','Other'].map((v) => <option key={v}>{v}</option>)}</select></label>
      <label htmlFor="maintenance-description" className="grid gap-2 text-sm font-semibold">Example issue<Textarea id="maintenance-description" required minLength={10} value={form.description} onChange={(e) => field('description',e.target.value)} data-testid="maintenance-description-input" /></label>
      <label htmlFor="maintenance-entry" className="flex items-start gap-3 border border-stone-300 bg-white p-4 text-sm"><input id="maintenance-entry" type="checkbox" checked={form.permission_to_enter} onChange={(e) => field('permission_to_enter',e.target.checked)} data-testid="maintenance-entry-permission-checkbox" />Example entry preference only — not real authorization to enter.</label>
      {error&&<p role="alert" className="text-sm text-red-800" data-testid="maintenance-error">{error}</p>}{confirmation&&<p role="status" className="text-sm text-green-800" data-testid="maintenance-confirmation">{confirmation}</p>}
      <Button disabled={loading||!PHASE0.seedsEnabled} className="h-12 bg-obsidian text-linen hover:bg-copper" data-testid="maintenance-submit-btn">{loading?<Loader2 className="h-4 w-4 animate-spin" />:<Wrench size={16} />}Record synthetic request</Button>
    </form>
  </DialogContent></Dialog>;
};