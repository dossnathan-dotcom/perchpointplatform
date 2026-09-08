import { useState } from "react";
import { Toaster } from "sonner";
import "@/App.css";
import { ClientDashboard } from "@/components/ClientDashboard";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { Listings } from "@/components/Listings";
import { LoginModal } from "@/components/LoginModal";
import { MarketMetrics } from "@/components/MarketMetrics";
import { Navbar } from "@/components/Navbar";
import { Neighborhoods } from "@/components/Neighborhoods";
import { Testimonials } from "@/components/Testimonials";
import { TourModal } from "@/components/TourModal";
import { Valuation } from "@/components/Valuation";
import { LISTINGS } from "@/data/siteData";

function App() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [user, setUser] = useState(null);
  const [tourProperty, setTourProperty] = useState(LISTINGS[0]);

  const openTour = (property = LISTINGS[0]) => {
    setTourProperty(property);
    setTourOpen(true);
  };

  const handleLogin = (account) => {
    setUser(account);
    setDashboardOpen(true);
  };

  const handleLogout = () => {
    setUser(null);
    setDashboardOpen(false);
  };

  return (
    <div className="min-h-screen bg-linen text-obsidian">
      <Navbar
        user={user}
        onLoginClick={() => setLoginOpen(true)}
        onDashboardOpen={() => setDashboardOpen(true)}
        onSchedule={() => openTour()}
      />
      <main>
        <Hero onSchedule={() => openTour()} />
        <MarketMetrics />
        <Listings onSchedule={openTour} />
        <Neighborhoods />
        <Valuation />
        <Testimonials />
      </main>
      <Footer onSchedule={() => openTour()} />

      <LoginModal open={loginOpen} onOpenChange={setLoginOpen} onSuccess={handleLogin} />
      <ClientDashboard
        user={user}
        open={dashboardOpen}
        onOpenChange={setDashboardOpen}
        onLogout={handleLogout}
        onSchedule={() => {
          setDashboardOpen(false);
          openTour();
        }}
      />
      <TourModal property={tourProperty} open={tourOpen} onOpenChange={setTourOpen} />
      <Toaster richColors position="top-center" />
    </div>
  );
}

export default App;
