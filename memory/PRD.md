# HawkVision Homes PRD

## Original Problem Statement
"Now, I am going to build a website for HawkVision homes. It's a relaty company, it should have mock log in, and have really good tranisition between headings and do it in creative ways while still keeping the CTA's you wold expect top find clear. Make sure this will convert, it should grab the users attention and keep it. This is in Cincinnati, OH."

Follow-up direction: the requested ChatGPT AI Models integration was explicitly withdrawn, so the delivered site contains no AI chat feature.

## User Personas
- Luxury buyer comparing private Cincinnati listings and neighborhood fit.
- Cincinnati seller who wants a fast home-value range before speaking with an advisor.
- Relocating professional who needs trusted local guidance and clear next steps.

## Core Requirements
- Conversion-focused HawkVision Homes landing page for Cincinnati, OH.
- Creative animated heading transitions without hiding expected CTAs.
- Mock login with realistic buyer and seller demo profiles.
- Featured properties, neighborhood positioning, proof points, tour requests, and valuation capture.
- FastAPI backend routes under `/api`, React frontend, MongoDB persistence for submitted leads and valuation requests.

## Implemented — July 2026
- Luxury/editorial visual system using obsidian, linen, copper, gold, Playfair Display, IBM Plex Sans, and JetBrains Mono.
- Sticky conversion navigation with Properties, Neighborhoods, Valuation, Results, Mock Login, and Schedule Tour.
- Hero with Cincinnati skyline imagery, automatic and manual kinetic heading transitions, clear portfolio/valuation/tour CTAs, and rapid search controls.
- Market ticker and Cincinnati micro-market metrics.
- Filterable featured listings for Mount Adams, Indian Hill, Hyde Park, and Over-The-Rhine.
- Neighborhood cards with lifestyle positioning and score badges.
- Frontend-only mock client portal with buyer and seller quick-fill credentials, saved homes, watchlist, buying position, logout, and tour CTA.
- Private tour modal connected to `POST /api/leads` and persisted to MongoDB.
- Instant home valuation form connected to `POST /api/valuation`; returns a preliminary range and persists requests.
- Testimonials/trust section and editorial footer with consultation CTA.
- Backend health, properties, lead, and valuation endpoints.
- Comprehensive data-testid coverage for key interactive elements.

## Current Status
- P0 remaining: none for the requested MVP.
- P1 remaining: listing detail pages, saved-home interactions before login, expanded neighborhood guides.
- P2 remaining: analytics/events, SEO content expansion, real brokerage content and imagery, production auth if the demo becomes a real portal.

## Prioritized Backlog
1. Add full listing detail pages with galleries, maps, property history, and inquiry forms.
2. Let anonymous visitors save homes and carry those saves into the mock portal.
3. Add deeper Cincinnati neighborhood guides with commute, school, and lifestyle context.
4. Add agent profile and consultation scheduling experience.
5. Add conversion analytics for CTA, valuation, tour, and filter interactions.

## Verification Completed
- `GET /api`, `GET /api/health`, `GET /api/properties`, `POST /api/leads`, and `POST /api/valuation` returned expected responses.
- Production frontend build completed successfully.
- Browser verification confirmed hero rendering, manual heading transition, buyer mock login, dashboard, logout, tour submission, valuation result, listing filtering, and sticky-header contrast.

## Mock Credentials
- VIP Buyer: buyer@hawkvision.com / hawk-demo
- Luxury Seller: seller@hawkvision.com / sell-demo
