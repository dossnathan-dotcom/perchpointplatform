import { IMAGES } from "@/data/siteData";

export const PROPERTY_DETAILS = {
  "mt-adams-overlook": {
    coordinates: { lat: 39.1087, lng: -84.4879 },
    address: "1088 St. Gregory Street, Cincinnati, OH 45202",
    gallery: [IMAGES.estate, IMAGES.living, IMAGES.riverfront],
    story:
      "Positioned above the city grid, this residence turns the Cincinnati skyline into a daily backdrop. Terraced outdoor rooms, gallery-scale walls, and a calm material palette create a private retreat minutes from downtown.",
    features: ["Skyline terrace", "Three-car garage", "Heated floors", "Wine gallery", "Smart glass", "Elevator"],
    taxes: "$18,420 / year",
    hoa: "None",
    daysPrivate: "21 days privately offered",
    priceHistory: [
      { label: "Private launch", value: "$1,285,000" },
      { label: "Prior renovation", value: "Completed 2024" },
      { label: "Competitive range", value: "$1.24M – $1.36M" },
    ],
  },
  "indian-hill-sanctuary": {
    coordinates: { lat: 39.2128, lng: -84.339 },
    address: "6200 Given Road, Cincinnati, OH 45243",
    gallery: [IMAGES.patio, IMAGES.estate, IMAGES.park],
    story:
      "A gated estate composed for privacy, recreation, and long-term legacy. Guest quarters, equestrian-ready acreage, and resort-style outdoor living give the property a rare sense of retreat inside Indian Hill.",
    features: ["6.2 private acres", "Resort pool", "Guest house", "Equestrian zoning", "Outdoor kitchen", "Five-car garage"],
    taxes: "$31,860 / year",
    hoa: "None",
    daysPrivate: "14 days privately offered",
    priceHistory: [
      { label: "Private launch", value: "$2,495,000" },
      { label: "Estate improvements", value: "$410K invested" },
      { label: "Competitive range", value: "$2.38M – $2.61M" },
    ],
  },
  "hyde-park-classic": {
    coordinates: { lat: 39.1395, lng: -84.4439 },
    address: "3510 Erie Avenue, Cincinnati, OH 45208",
    gallery: [IMAGES.living, IMAGES.lounge, IMAGES.park],
    story:
      "Classic Hyde Park architecture meets a carefully edited interior renovation. The home keeps its historic rhythm while adding the kitchen, light, and flexible work spaces today’s buyers expect.",
    features: ["Restored millwork", "Chef’s kitchen", "Sunroom", "Walk to Hyde Park Square", "Home office", "New systems"],
    taxes: "$12,940 / year",
    hoa: "None",
    daysPrivate: "New this week",
    priceHistory: [
      { label: "Private launch", value: "$875,000" },
      { label: "Kitchen renovation", value: "Completed 2025" },
      { label: "Competitive range", value: "$842K – $918K" },
    ],
  },
  "otr-penthouse": {
    coordinates: { lat: 39.109, lng: -84.515 },
    address: "1415 Vine Street, Cincinnati, OH 45202",
    gallery: [IMAGES.lounge, IMAGES.living, IMAGES.hero],
    story:
      "A design-forward penthouse above one of Over-The-Rhine’s most storied blocks. Warehouse windows, exposed masonry, and a rooftop deck place the neighborhood’s dining and culture at your doorstep.",
    features: ["Private rooftop deck", "14-foot ceilings", "Exposed brick", "Two parking spaces", "Freight elevator", "Custom lighting"],
    taxes: "$9,780 / year",
    hoa: "$640 / month",
    daysPrivate: "By appointment only",
    priceHistory: [
      { label: "Private launch", value: "$1,190,000" },
      { label: "Rooftop upgrade", value: "Completed 2023" },
      { label: "Competitive range", value: "$1.12M – $1.24M" },
    ],
  },
};
