import { Building2, CalendarCheck, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";

const links = [
  { label: "Properties", href: "/#properties" },
  { label: "Neighborhoods", href: "/#neighborhoods" },
  { label: "Advisor", href: "/#advisor" },
  { label: "Valuation", href: "/#valuation" },
  { label: "Results", href: "/#results" },
];

export const Navbar = ({ user, onLoginClick, onDashboardOpen, onSchedule }) => {
  return (
    <header className="fixed inset-x-0 top-0 z-40 border-b border-white/10 bg-obsidian/90 text-linen shadow-2xl shadow-black/10 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-5 sm:px-8">
        <a href="/" className="flex items-center gap-3" data-testid="navbar-brand-logo">
          <span className="flex h-11 w-11 items-center justify-center rounded-full border border-gold/40 bg-gold/10 text-gold">
            <Building2 className="h-5 w-5" />
          </span>
          <span>
            <span className="block font-heading text-xl font-bold tracking-tight">HawkVision</span>
            <span className="block font-mono text-[10px] uppercase tracking-[0.28em] text-linen/60">
              Cincinnati Homes
            </span>
          </span>
        </a>

        <nav className="hidden items-center gap-7 lg:flex" data-testid="navbar-nav-links">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-linen/70 transition-colors duration-300 hover:text-gold"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            className="hidden border-white/20 bg-white/5 text-linen hover:bg-white/10 hover:text-linen sm:inline-flex"
            onClick={user ? onDashboardOpen : onLoginClick}
            data-testid="navbar-login-btn"
          >
            <UserRound className="h-4 w-4" />
            {user ? "Client Portal" : "Mock Login"}
          </Button>
          <Button
            className="bg-gold text-obsidian hover:bg-goldSoft"
            onClick={onSchedule}
            data-testid="navbar-schedule-tour-btn"
          >
            <CalendarCheck className="h-4 w-4" />
            Schedule Tour
          </Button>
        </div>
      </div>
    </header>
  );
};
