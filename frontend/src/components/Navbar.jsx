import { useState } from "react";
import { Building2, Menu, Wrench, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const links = [
  ["Available Rentals", "/#rentals"],
  ["Properties", "/#properties"],
  ["How to Apply", "/#how-to-apply"],
  ["Resident Resources", "/#resident-resources"],
  ["Maintenance", "/#maintenance"],
  ["About", "/#about"],
];

export const Navbar = ({ onLoginClick, onMaintenance }) => {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-obsidian/95 text-linen shadow-2xl shadow-black/10 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between gap-4 px-5 sm:px-8">
        <a href="/" className="flex min-w-0 items-center gap-3" data-testid="nav-brand-hawkvision">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-gold/40 bg-gold/10 text-gold"><Building2 className="h-5 w-5" /></span>
          <span className="min-w-0">
            <span className="block truncate font-heading text-lg font-bold">HawkVision Homes</span>
            <span className="block truncate font-mono text-[9px] uppercase tracking-[0.2em] text-linen/60">Powered by PerchPoint OS</span>
          </span>
        </a>

        <nav className="hidden items-center gap-5 xl:flex" data-testid="navbar-nav-links">
          {links.map(([label, href]) => <a key={href} href={href} className="text-xs font-semibold text-linen/70 transition-colors hover:text-gold" data-testid={`nav-link-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</a>)}
        </nav>

        <div className="flex items-center gap-2">
          <Button variant="outline" className="hidden border-white/20 bg-white/5 text-linen hover:bg-white/10 hover:text-linen md:inline-flex" onClick={onMaintenance} data-testid="navbar-maintenance-btn">
            <Wrench className="h-4 w-4" /> Maintenance
          </Button>
          <Button className="bg-copper text-linen hover:bg-copperDark" onClick={onLoginClick} data-testid="nav-login-perchpoint-btn">Sign in to PerchPoint</Button>
          <button className="flex h-10 w-10 items-center justify-center rounded-md border border-white/15 xl:hidden" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation" data-testid="navbar-mobile-menu-btn">
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {menuOpen && (
        <nav className="border-t border-white/10 bg-obsidian px-5 py-5 xl:hidden" data-testid="navbar-mobile-menu">
          <div className="mx-auto grid max-w-7xl gap-1">
            {links.map(([label, href]) => <a key={href} href={href} onClick={() => setMenuOpen(false)} className="rounded-md px-3 py-3 text-sm font-semibold text-linen/75 hover:bg-white/5 hover:text-gold" data-testid={`mobile-nav-link-${label.toLowerCase().replaceAll(" ", "-")}`}>{label}</a>)}
          </div>
        </nav>
      )}
    </header>
  );
};