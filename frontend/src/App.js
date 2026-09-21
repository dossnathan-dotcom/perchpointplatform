import { useState } from "react";
import { BrowserRouter, Link, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Building2, LogIn } from "lucide-react";
import { Toaster } from "sonner";
import "@/App.css";
import { AboutHawkVision } from "@/components/AboutHawkVision";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { HowToApply } from "@/components/HowToApply";
import { Listings } from "@/components/Listings";
import { LoginModal } from "@/components/LoginModal";
import { MaintenanceModal } from "@/components/MaintenanceModal";
import { Navbar } from "@/components/Navbar";
import { Neighborhoods } from "@/components/Neighborhoods";
import { PerchPointPortal } from "@/components/PerchPointPortal";
import { PropertyDetailPage } from "@/components/PropertyDetailPage";
import { PropertyHierarchyView } from "@/components/PropertyHierarchyView";
import { ResidentResources } from "@/components/ResidentResources";
import { TourModal } from "@/components/TourModal";
import { Button } from "@/components/ui/button";
import { RENTALS } from "@/data/siteData";
import FoundationPage from "@/components/FoundationPage";

const PortalGate = ({ onLogin }) => (
  <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-obsidian px-5 text-linen" data-testid="perchpoint-portal-gate">
    <div className="texture-grid absolute inset-0" />
    <div className="relative max-w-xl text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center bg-copper text-white"><Building2 className="h-6 w-6" /></span><p className="mt-7 font-mono text-xs uppercase tracking-[0.24em] text-gold">PerchPoint</p><h1 className="mt-4 font-heading text-5xl font-bold">Property operations, with the right access for every role.</h1><p className="mt-5 leading-7 text-linen/60">Enter the seeded Phase 0 workspace preview. Production identity and authorization are intentionally not active yet.</p><div className="mt-8 flex flex-wrap justify-center gap-3"><Button className="bg-copper text-white hover:bg-copperDark" onClick={onLogin} data-testid="portal-gate-login-btn"><LogIn className="h-4 w-4" /> Sign in to preview</Button><Button asChild variant="outline" className="border-white/20 bg-white/5 text-linen hover:bg-white/10 hover:text-linen"><Link to="/" data-testid="portal-gate-public-site-link">Return to HawkVision</Link></Button></div></div>
  </main>
);

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginRole, setLoginRole] = useState("resident");
  const [requestOpen, setRequestOpen] = useState(false);
  const [maintenanceOpen, setMaintenanceOpen] = useState(false);
  const [requestIntent, setRequestIntent] = useState("showing");
  const [requestProperty, setRequestProperty] = useState(RENTALS[0]);

  const openLogin = (role = "resident") => { setLoginRole(role); setLoginOpen(true); };
  const openRequest = (property = RENTALS[0], intent = "showing") => { setRequestProperty(intent === 'contact' ? null : property); setRequestIntent(intent); setRequestOpen(true); };
  const handleLogin = (account) => { navigate(`/perchpoint/${account.id}`); };
  const isPortal = location.pathname.startsWith("/perchpoint");

  if (location.pathname.startsWith('/foundation')) return <Routes><Route path="/foundation/:sectionId?" element={<FoundationPage />} /></Routes>;

  if (isPortal) {
    return <><Routes><Route path="/perchpoint" element={<PortalGate onLogin={() => openLogin("owner")} />} /><Route path="/perchpoint/:roleId/:viewId?" element={<PerchPointPortal />} /></Routes><LoginModal open={loginOpen} onOpenChange={setLoginOpen} onSuccess={handleLogin} initialRole={loginRole} /><Toaster richColors position="top-center" /></>;
  }

  return (
    <div className="min-h-screen bg-linen text-obsidian">
      <Navbar onLoginClick={() => openLogin("resident")} onMaintenance={() => setMaintenanceOpen(true)} />
      <Routes>
        <Route path="/" element={<main><Hero onSchedule={() => openRequest(RENTALS[0], "showing")} onMaintenance={() => setMaintenanceOpen(true)} /><Listings onRequest={openRequest} /><PropertyHierarchyView /><HowToApply onApply={() => openRequest(RENTALS[0], "application")} /><ResidentResources onMaintenance={() => setMaintenanceOpen(true)} onLogin={() => openLogin("resident")} /><Neighborhoods /><AboutHawkVision /></main>} />
        <Route path="/property/:propertyId" element={<PropertyDetailPage onRequest={openRequest} />} />
        <Route path="/rentals/:unitId" element={<PropertyDetailPage onRequest={openRequest} />} />
        <Route path="*" element={<main className="min-h-[70vh] px-5 pb-20 pt-40" data-testid="not-found-page"><h1 className="font-heading text-4xl">This page is not here.</h1><Link to="/" className="mt-6 block underline" data-testid="not-found-home-link">Return to HawkVision Homes</Link></main>} />
      </Routes>
      <Footer onContact={() => openRequest(undefined, "contact")} onMaintenance={() => setMaintenanceOpen(true)} />
      <LoginModal open={loginOpen} onOpenChange={setLoginOpen} onSuccess={handleLogin} initialRole={loginRole} />
      <TourModal property={requestProperty} intent={requestIntent} open={requestOpen} onOpenChange={setRequestOpen} />
      <MaintenanceModal open={maintenanceOpen} onOpenChange={setMaintenanceOpen} />
      <Toaster richColors position="top-center" />
    </div>
  );
}

export default function App() {
  return <BrowserRouter><AppContent /></BrowserRouter>;
}