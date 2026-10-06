import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Link, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { Building2, LogIn } from "lucide-react";
import "@/App.css";
import { AboutHawkVision } from "@/components/AboutHawkVision";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { HowToApply } from "@/components/HowToApply";
import { Listings } from "@/components/Listings";
import { Navbar } from "@/components/Navbar";
import { Neighborhoods } from "@/components/Neighborhoods";
import { ResidentResources } from "@/components/ResidentResources";
import { AppErrorBoundary } from "@/components/AppErrorBoundary";
import { Button } from "@/components/ui/button";
import { startSentry } from "@/sentry";
import { SkipLink } from "@/design-system/components";
import { applyDocumentTheme } from "@/design-system/theme";

const PerchPointPortal = lazy(() => import("@/components/PerchPointPortal").then((module) => ({ default: module.PerchPointPortal })));
const Phase5Workspace = lazy(() => import("@/components/portal/Phase5Workspace").then((module) => ({ default: module.Phase5Workspace })));
const PortfolioAdmin = lazy(() => import("@/components/portal/PortfolioAdmin").then((module) => ({ default: module.PortfolioAdmin })));
const Phase6SignIn = lazy(() => import("@/components/portal/Phase6SignIn").then((module) => ({ default: module.Phase6SignIn })));
const Phase6IdentityFlow = lazy(() => import("@/components/portal/Phase6Identity").then((module) => ({ default: module.Phase6IdentityFlow })));
const Phase6AccessWorkspace = lazy(() => import("@/components/portal/Phase6Access").then((module) => ({ default: module.Phase6AccessWorkspace })));
const Phase6BoundaryPage = lazy(() => import("@/components/portal/Phase6Access").then((module) => ({ default: module.Phase6BoundaryPage })));
const FoundationPage = lazy(() => import("@/components/FoundationPage"));
const ReferenceOperations = lazy(() => import("@/components/ReferenceOperations").then((module) => ({ default: module.ReferenceOperations })));
const PropertyDetailPage = lazy(() => import("@/components/PropertyDetailPage").then((module) => ({ default: module.PropertyDetailPage })));
const RentalsIndex = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.RentalsIndex })));
const ApplyGuide = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.ApplyGuide })));
const ManagedPage = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.ManagedPage })));
const ContactPage = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.ContactPage })));
const StaffContent = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.StaffContent })));
const PublicStatus = lazy(() => import("@/components/public/PublicSite").then((module) => ({ default: module.PublicStatus })));
const LoginModal = lazy(() => import("@/components/LoginModal").then((module) => ({ default: module.LoginModal })));
const TourModal = lazy(() => import("@/components/TourModal").then((module) => ({ default: module.TourModal })));
const MaintenanceModal = lazy(() => import("@/components/MaintenanceModal").then((module) => ({ default: module.MaintenanceModal })));
const Laboratory = process.env.NODE_ENV === "production" ? null : lazy(() => import("@/design-system/laboratory"));
const routePending = <main id="main" className="min-h-screen bg-obsidian px-6 py-24 text-linen"><p role="status">Loading workspace.</p></main>;

const PortalGate = ({ onLogin }) => (
  <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-obsidian px-5 text-linen" data-testid="perchpoint-portal-gate">
    <div className="texture-grid absolute inset-0" />
    <div className="relative max-w-xl text-center"><span className="mx-auto flex h-14 w-14 items-center justify-center bg-copper text-white"><Building2 className="h-6 w-6" /></span><p className="mt-7 font-mono text-xs uppercase tracking-[0.24em] text-gold">PerchPoint preview</p><h1 className="mt-4 font-heading text-5xl font-bold">Explore synthetic role workspaces.</h1><p className="mt-5 leading-7 text-linen/60">This explicit preview cannot authenticate a user or create authority. Use unified sign-in for connected identity workflows.</p><div className="mt-8 flex flex-wrap justify-center gap-3"><Button className="bg-copper text-white hover:bg-copperDark" onClick={onLogin} data-testid="portal-gate-login-btn"><LogIn className="h-4 w-4" /> Open synthetic preview</Button><Button asChild variant="outline" className="border-white/20 bg-white/5 text-linen hover:bg-white/10 hover:text-linen"><Link to="/sign-in">Unified sign-in</Link></Button><Button asChild variant="outline" className="border-white/20 bg-white/5 text-linen hover:bg-white/10 hover:text-linen"><Link to="/" data-testid="portal-gate-public-site-link">Return to HawkVision</Link></Button></div></div>
  </main>
);

function PublicLayout({ onLogin, onMaintenance, onContact }) {
  return <div className="min-h-screen bg-linen text-obsidian"><SkipLink /><Navbar onLoginClick={onLogin} onMaintenance={onMaintenance} /><Outlet /><Footer onContact={onContact} onMaintenance={onMaintenance} /></div>;
}

const PageNotFound = () => <main className="min-h-screen bg-obsidian px-5 pb-20 pt-40 text-linen" data-testid="not-found-page"><h1 className="font-heading text-4xl">This page is not here.</h1><Link to="/" className="mt-6 block underline" data-testid="not-found-home-link">Return to HawkVision Homes</Link></main>;

export function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [loginLocationKey, setLoginLocationKey] = useState(null);
  const [loginRole, setLoginRole] = useState("resident");
  const [requestOpen, setRequestOpen] = useState(false);
  const [maintenanceOpen, setMaintenanceOpen] = useState(false);
  const [requestIntent, setRequestIntent] = useState("showing");
  const [requestProperty, setRequestProperty] = useState(null);

  const loginOpen = loginLocationKey === location.key;
  const setLoginOpen = (open) => setLoginLocationKey(open ? location.key : null);
  const openLogin = (role = "resident") => { setLoginRole(role); setLoginOpen(true); };
  const openRequest = (property = null, intent = "showing") => { setRequestProperty(intent === 'contact' ? null : property); setRequestIntent(intent); setRequestOpen(true); };
  const handleLogin = (account) => { setLoginLocationKey(null); navigate(`/perchpoint/${account.id}`); };
  useEffect(() => {
    setLoginLocationKey(null);
    setRequestOpen(false);
    setMaintenanceOpen(false);
  }, [location.key]);
  useEffect(() => { applyDocumentTheme(location.pathname); }, [location.pathname]);

  return (
    <>
      <Routes>
        <Route element={<PublicLayout onLogin={() => navigate("/sign-in")} onMaintenance={() => setMaintenanceOpen(true)} onContact={() => openRequest(undefined, "contact")} />}>
        <Route path="/" element={<main id="main"><Hero onSchedule={() => document.getElementById('rentals')?.scrollIntoView({ behavior: 'smooth' })} onMaintenance={() => setMaintenanceOpen(true)} /><Listings /><HowToApply onApply={() => document.getElementById('rentals')?.scrollIntoView({ behavior: 'smooth' })} /><ResidentResources onMaintenance={() => setMaintenanceOpen(true) } onLogin={() => navigate("/sign-in")} /><Neighborhoods /><AboutHawkVision /></main>} />
        <Route path="/rentals" element={<Suspense fallback={routePending}><RentalsIndex /></Suspense>} />
        <Route path="/apply" element={<Suspense fallback={routePending}><ApplyGuide /></Suspense>} />
        <Route path="/resources" element={<Suspense fallback={routePending}><ManagedPage slug="resources" testId="resources-page" /></Suspense>} />
        <Route path="/faq" element={<Suspense fallback={routePending}><ManagedPage slug="faq" testId="faq-page" /></Suspense>} />
        <Route path="/maintenance" element={<Suspense fallback={routePending}><ManagedPage slug="maintenance" testId="maintenance-page" /></Suspense>} />
        <Route path="/about" element={<Suspense fallback={routePending}><ManagedPage slug="about" testId="about-page" /></Suspense>} />
        <Route path="/contact" element={<Suspense fallback={routePending}><ContactPage /></Suspense>} />
        <Route path="/privacy" element={<Suspense fallback={routePending}><ManagedPage slug="privacy" testId="privacy-page" /></Suspense>} />
        <Route path="/terms" element={<Suspense fallback={routePending}><ManagedPage slug="terms" testId="terms-page" /></Suspense>} />
        <Route path="/staff/content" element={<Suspense fallback={routePending}><StaffContent /></Suspense>} />
        <Route path="/status/410" element={<Suspense fallback={routePending}><PublicStatus code="410" title="This page has been removed" message="The address is gone. No draft is shown." testId="gone-page" /></Suspense>} />
        <Route path="/status/429" element={<Suspense fallback={routePending}><PublicStatus code="429" title="Too many requests" message="Wait and try again. Nothing was saved." testId="limited-page" /></Suspense>} />
        <Route path="/status/503" element={<Suspense fallback={routePending}><PublicStatus code="503" title="Temporarily unavailable" message="The public site cannot complete this request." testId="unavailable-page" /></Suspense>} />
        <Route path="/property/:propertyId" element={<Suspense fallback={routePending}><PropertyDetailPage onRequest={openRequest} /></Suspense>} />
        <Route path="/rentals/:unitId" element={<Suspense fallback={routePending}><PropertyDetailPage onRequest={openRequest} /></Suspense>} />
        </Route>
        <Route path="/sign-in" element={<Suspense fallback={routePending}><Phase6SignIn /></Suspense>} />
        <Route path="/invitation" element={<Suspense fallback={routePending}><Phase6IdentityFlow mode="invitation" /></Suspense>} />
        <Route path="/password-reset" element={<Suspense fallback={routePending}><Phase6IdentityFlow mode="password-reset" /></Suspense>} />
        <Route path="/mfa" element={<Suspense fallback={routePending}><Phase6IdentityFlow mode="mfa" /></Suspense>} />
        <Route path="/access/onboarding" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="onboarding" /></Suspense>} />
        <Route path="/access/security" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="security" /></Suspense>} />
        <Route path="/access/users-access" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="users-access" /></Suspense>} />
        <Route path="/access/delegations" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="delegations" /></Suspense>} />
        <Route path="/access/access-requests" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="access-requests" /></Suspense>} />
        <Route path="/access/access-reviews" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="access-reviews" /></Suspense>} />
        <Route path="/access/vendor-access" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="vendor-access" /></Suspense>} />
        <Route path="/access/maintenance-history" element={<Suspense fallback={routePending}><Phase6AccessWorkspace surface="maintenance-history" /></Suspense>} />
        <Route path="/access-denied" element={<Suspense fallback={routePending}><Phase6BoundaryPage kind="access-denied" /></Suspense>} />
        <Route path="/session-expired" element={<Suspense fallback={routePending}><Phase6BoundaryPage kind="session-expired" /></Suspense>} />
        <Route path="/perchpoint" element={<PortalGate onLogin={() => openLogin("owner")} />} />
        <Route path="/perchpoint/:roleId/phase5/:center" element={<Suspense fallback={routePending}><Phase5Workspace /></Suspense>} />
        <Route path="/perchpoint/:roleId/listing-administration" element={<Suspense fallback={routePending}><PortfolioAdmin /></Suspense>} />
        <Route path="/perchpoint/:roleId/:viewId?" element={<Suspense fallback={routePending}><PerchPointPortal key={location.key} /></Suspense>} />
        <Route path="/perchpoint/*" element={<PageNotFound />} />
        <Route path="/foundation/:sectionId?" element={<Suspense fallback={routePending}><FoundationPage key={location.key} /></Suspense>} />
        <Route path="/reference" element={<Suspense fallback={routePending}><ReferenceOperations /></Suspense>} />
        {Laboratory ? <Route path="/design-system" element={<Suspense fallback={routePending}><Laboratory /></Suspense>} /> : null}
        <Route path="*" element={<PageNotFound />} />
      </Routes>
      {loginOpen && <Suspense fallback={null}><LoginModal key={location.key} open onOpenChange={setLoginOpen} onSuccess={handleLogin} initialRole={loginRole} /></Suspense>}
      {requestOpen && <Suspense fallback={null}><TourModal property={requestProperty} intent={requestIntent} open onOpenChange={setRequestOpen} /></Suspense>}
      {maintenanceOpen && <Suspense fallback={null}><MaintenanceModal open onOpenChange={setMaintenanceOpen} /></Suspense>}
    </>
  );
}

startSentry();

export default function App() {
  return <AppErrorBoundary><BrowserRouter><AppContent /></BrowserRouter></AppErrorBoundary>;
}