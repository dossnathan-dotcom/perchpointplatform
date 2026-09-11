import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import "@/App.css";
import { AgentStory } from "@/components/AgentStory";
import { BuyerQuiz } from "@/components/BuyerQuiz";
import { ClientDashboard } from "@/components/ClientDashboard";
import { Footer } from "@/components/Footer";
import { Hero } from "@/components/Hero";
import { Listings } from "@/components/Listings";
import { LoginModal } from "@/components/LoginModal";
import { MarketMetrics } from "@/components/MarketMetrics";
import { Navbar } from "@/components/Navbar";
import { Neighborhoods } from "@/components/Neighborhoods";
import { PropertyDetailPage } from "@/components/PropertyDetailPage";
import { Testimonials } from "@/components/Testimonials";
import { TourModal } from "@/components/TourModal";
import { Valuation } from "@/components/Valuation";
import { LISTINGS } from "@/data/siteData";

function App() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [tourOpen, setTourOpen] = useState(false);
  const [tourIntent, setTourIntent] = useState("private_tour");
  const [user, setUser] = useState(null);
  const [tourProperty, setTourProperty] = useState(LISTINGS[0]);
  const [savedIds, setSavedIds] = useState(() => {
    try {
      return JSON.parse(window.localStorage.getItem("hawkvision-saved-homes") || "[]");
    } catch {
      return [];
    }
  });

  useEffect(() => {
    window.localStorage.setItem("hawkvision-saved-homes", JSON.stringify(savedIds));
  }, [savedIds]);

  const toggleSaved = (propertyId) => {
    setSavedIds((current) =>
      current.includes(propertyId)
        ? current.filter((item) => item !== propertyId)
        : [...current, propertyId]
    );
  };

  const openTour = (property = LISTINGS[0], intent = "private_tour") => {
    setTourProperty(property);
    setTourIntent(intent);
    setTourOpen(true);
  };

  const openConsultation = () => openTour(LISTINGS[0], "consultation");

  const handleLogin = (account) => {
    setUser({
      ...account,
      savedIds: [...new Set([...account.savedIds, ...savedIds])],
    });
    setDashboardOpen(true);
  };

  const handleLogout = () => {
    setUser(null);
    setDashboardOpen(false);
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-linen text-obsidian">
        <Navbar
          user={user}
          onLoginClick={() => setLoginOpen(true)}
          onDashboardOpen={() => setDashboardOpen(true)}
          onSchedule={() => openTour()}
        />
        <Routes>
          <Route
            path="/"
            element={
              <main>
                <Hero onSchedule={() => openTour()} />
                <MarketMetrics />
                <Listings onSchedule={openTour} savedIds={savedIds} onToggleSaved={toggleSaved} />
                <Neighborhoods />
                <AgentStory onBookConsultation={openConsultation} />
                <Valuation />
                <BuyerQuiz onConsultation={openConsultation} />
                <Testimonials />
              </main>
            }
          />
          <Route
            path="/property/:propertyId"
            element={<PropertyDetailPage onSchedule={openTour} savedIds={savedIds} onToggleSaved={toggleSaved} />}
          />
        </Routes>
        <Footer onSchedule={openConsultation} />

        <LoginModal open={loginOpen} onOpenChange={setLoginOpen} onSuccess={handleLogin} />
        <ClientDashboard
          user={user}
          savedIds={savedIds}
          open={dashboardOpen}
          onOpenChange={setDashboardOpen}
          onLogout={handleLogout}
          onSchedule={() => {
            setDashboardOpen(false);
            openTour();
          }}
        />
        <TourModal property={tourProperty} intent={tourIntent} open={tourOpen} onOpenChange={setTourOpen} />
        <Toaster richColors position="top-center" />
      </div>
    </BrowserRouter>
  );
}

export default App;
