import { useState } from "react";
import { Building2, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EnvironmentBanner } from "@/components/EnvironmentBanner";

const links = [
  ["Available Rentals", "/#rentals"],
  ["Properties", "/#properties"],
  ["How to Apply", "/#how-to-apply"],
  ["Resident Resources", "/#resident-resources"],
  ["Maintenance", "/#maintenance"],
  ["About", "/#about"],
  ["Contact HawkVision", "/#contact"],
];

export const Navbar = ({ onLoginClick }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-white/30 bg-obsidian text-linen" data-testid="public-header">
      <EnvironmentBanner />
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-4 px-5 sm:px-8">
        <a href="/" className="flex min-w-0 items-center gap-3" data-testid="nav-brand-hawkvision">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-gold/40 bg-gold/10 text-gold"><Building2 className="h-5 w-5" /></span>
          <span className="min-w-0">
            <span className="block font-heading text-base font-bold sm:text-lg">HawkVision Homes</span>
            <span className="block font-mono text-[9px] uppercase text-linen">Powered by PerchPoint</span>
          </span>
        </a>

        <nav className="hidden items-center gap-4 xl:flex" data-testid="navbar-nav-links">
          {links.map(([label, href]) => <a key={href} href={href} className="py-3 text-xs font-semibold text-linen transition-colors hover:text-gold" data-testid={`nav-link-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</a>)}
        </nav>

        <div className="flex items-center gap-2">
          <Button className="hidden bg-copper text-white hover:bg-copperDark sm:inline-flex" onClick={onLoginClick} data-testid="nav-login-perchpoint-btn">Sign in to PerchPoint</Button>
          <button className="flex h-11 w-11 items-center justify-center border border-white/50 xl:hidden" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen} aria-controls="mobile-navigation" aria-label="Toggle navigation" data-testid="navbar-mobile-menu-btn">
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {menuOpen && (
        <nav id="mobile-navigation" className="max-h-[calc(100dvh-5rem)] overflow-y-auto border-t border-white/30 bg-obsidian px-5 py-5 xl:hidden" data-testid="navbar-mobile-menu">
          <div className="mx-auto grid max-w-7xl gap-1">
            {links.map(([label, href]) => <a key={href} href={href} onClick={() => setMenuOpen(false)} className="rounded-md px-3 py-3 text-sm font-semibold text-linen/75 hover:bg-white/5 hover:text-gold" data-testid={`mobile-nav-link-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</a>)}
            <Button className="mt-3 bg-copper text-white" onClick={() => {setMenuOpen(false);onLoginClick();}} data-testid="mobile-signin-btn">Sign in to PerchPoint</Button>
          </div>
        </nav>
      )}
    </header>
  );
};