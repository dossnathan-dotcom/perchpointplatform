export const IMAGES = {
  hero: "https://images.unsplash.com/photo-1695782142250-963d4067ead8?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHwyfHxjaW5jaW5uYXRpJTIwc2t5bGluZSUyMG1vZGVybiUyMGVzdGF0ZXxlbnwwfHx8fDE3ODg5MDQ1MDF8MA&ixlib=rb-4.1.0&q=85",
  riverfront: "https://images.unsplash.com/photo-1592159784618-f1f74127d773?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHw0fHxjaW5jaW5uYXRpJTIwc2t5bGluZSUyMG1vZGVybiUyMGVzdGF0ZXxlbnwwfHx8fDE3ODg5MDQ1MDF8MA&ixlib=rb-4.1.0&q=85",
  park: "https://images.unsplash.com/photo-1663031065897-bd372ff85f75?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NzV8MHwxfHNlYXJjaHwzfHxjaW5jaW5uYXRpJTIwc2t5bGluZSUyMG1vZGVybiUyMGVzdGF0ZXxlbnwwfHx8fDE3ODg5MDQ1MDF8MA&ixlib=rb-4.1.0&q=85",
  estate: "https://images.unsplash.com/photo-1781264896316-f47aef24272d?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzV8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBjaW5jaW5uYXRpJTIwYXJjaGl0ZWN0dXJlJTIwbW9kZXJuJTIwaG9tZXxlbnwwfHx8fDE3ODg5MDQ1MDF8MA&ixlib=rb-4.1.0&q=85",
  living: "https://images.unsplash.com/photo-1642976975710-1d8890dbf5ab?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzd8MHwxfHNlYXJjaHwzfHxtb2Rlcm4lMjBsdXh1cnklMjB2aWxsYSUyMGxpdmluZyUyMHJvb218ZW58MHx8fHwxNzg4OTA0NTA1fDA&ixlib=rb-4.1.0&q=85",
  lounge: "https://images.unsplash.com/photo-1724582586495-d050726cf354?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBsdXh1cnklMjB2aWxsYSUyMGxpdmluZyUyMHJvb218ZW58MHx8fHwxNzg4OTA0NTA1fDA&ixlib=rb-4.1.0&q=85",
  patio: "https://images.unsplash.com/photo-1777003589733-91fe81465228?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzMzV8MHwxfHNlYXJjaHwzfHxsdXh1cnklMjBjaW5jaW5uYXRpJTIwYXJjaGl0ZWN0dXJlJTIwbW9kZXJuJTIwaG9tZXxlbnwwfHx8fDE3ODg5MDQ1MDF8MA&ixlib=rb-4.1.0&q=85",
};

export const HEADLINES = [
  {
    tag: "Perspective",
    title: "Look beyond the ordinary Cincinnati skyline.",
    subtitle:
      "Curated residential gems from Mount Adams bluff views to Indian Hill equestrian sanctuaries.",
  },
  {
    tag: "Precision",
    title: "See value before the market catches up.",
    subtitle:
      "Micro-market comps, pricing signals, and private listing intelligence shaped for your next move.",
  },
  {
    tag: "Access",
    title: "Tour private portfolios before they hit the MLS.",
    subtitle:
      "Discreet opportunities across Over-The-Rhine, Hyde Park, Walnut Hills, and Cincinnati’s seven hills.",
  },
];

export const LISTINGS = [
  {
    id: "mt-adams-overlook",
    title: "Mount Adams Skyline Overlook",
    neighborhood: "Mount Adams",
    price: 1285000,
    beds: 4,
    baths: 3.5,
    sqft: 3820,
    image: IMAGES.estate,
    tag: "Private portfolio",
    note: "Terraced views, sculptural architecture, and a five-minute glide to downtown.",
  },
  {
    id: "indian-hill-sanctuary",
    title: "Indian Hill Equestrian Sanctuary",
    neighborhood: "Indian Hill",
    price: 2495000,
    beds: 6,
    baths: 5.5,
    sqft: 7400,
    image: IMAGES.patio,
    tag: "Exclusive",
    note: "Gated acreage, guest quarters, resort-caliber pool, and complete privacy.",
  },
  {
    id: "hyde-park-classic",
    title: "Hyde Park Restored Classic",
    neighborhood: "Hyde Park",
    price: 875000,
    beds: 4,
    baths: 3,
    sqft: 2960,
    image: IMAGES.living,
    tag: "New this week",
    note: "Historic character with a polished chef’s kitchen near Hyde Park Square.",
  },
  {
    id: "otr-penthouse",
    title: "Over-The-Rhine Historic Penthouse",
    neighborhood: "Over-The-Rhine",
    price: 1190000,
    beds: 3,
    baths: 3,
    sqft: 2480,
    image: IMAGES.lounge,
    tag: "By appointment",
    note: "Warehouse-scale windows, exposed brick, and a rooftop deck above Vine Street.",
  },
];

export const NEIGHBORHOODS = [
  {
    name: "Mount Adams",
    image: IMAGES.riverfront,
    score: "98",
    detail: "Bluff views, walkable pubs, and skyline terraces.",
  },
  {
    name: "Hyde Park",
    image: IMAGES.park,
    score: "96",
    detail: "Tree-lined classics near the Square and Ault Park.",
  },
  {
    name: "Indian Hill",
    image: IMAGES.patio,
    score: "99",
    detail: "Estate lots, equestrian heritage, and rare seclusion.",
  },
  {
    name: "Over-The-Rhine",
    image: IMAGES.hero,
    score: "94",
    detail: "Historic architecture, dining, and design-forward lofts.",
  },
];

export const MOCK_ACCOUNTS = [
  {
    email: "buyer@hawkvision.com",
    password: "hawk-demo",
    name: "Julian Vance",
    role: "VIP Private Buyer",
    watchlist: "Indian Hill + Hyde Park",
    limit: "$2.85M pre-approved",
    savedIds: ["mt-adams-overlook", "indian-hill-sanctuary", "hyde-park-classic"],
  },
  {
    email: "seller@hawkvision.com",
    password: "sell-demo",
    name: "Elena Rostova",
    role: "Exclusive Seller",
    watchlist: "Mount Adams Bluff",
    limit: "$1.42M estimated value",
    savedIds: ["mt-adams-overlook"],
  },
];

export const TESTIMONIALS = [
  {
    quote:
      "HawkVision found us a Mount Adams home that never reached the public market. Their pricing guidance was surgical.",
    name: "Dr. Maya Ellison",
    detail: "Relocated from Chicago to Mount Adams",
  },
  {
    quote:
      "They positioned our Hyde Park home beautifully and negotiated a clean offer above asking in six days.",
    name: "Marcus & Lauren Bell",
    detail: "Sold in Hyde Park",
  },
  {
    quote:
      "The private tour process felt effortless. Every property matched our brief instead of wasting our weekends.",
    name: "Priya Shah",
    detail: "Purchased in Indian Hill",
  },
];
