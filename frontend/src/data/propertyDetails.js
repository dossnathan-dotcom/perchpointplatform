import { IMAGES } from "@/data/siteData";

export const PROPERTY_DETAILS = {
  "412-elm-unit-a": {
    coordinates: { lat: 39.1031, lng: -84.512 },
    gallery: [IMAGES.mixedUse, IMAGES.bakery, IMAGES.skyline],
    overview: "Residence A sits above a neighborhood commercial space in a mixed-use building organized around separate leases, utilities, access instructions, and maintenance records for every unit.",
    features: ["Secure common entry", "In-unit laundry", "Central air", "Separate utility meters", "Managed common areas", "Online resident portal"],
    leaseTerm: "12-month lease",
    parking: "Nearby options disclosed before application",
  },
  "clifton-duplex-unit-b": {
    coordinates: { lat: 39.145, lng: -84.52 },
    gallery: [IMAGES.duplex, IMAGES.skyline, IMAGES.mixedUse],
    overview: "A separately managed home within a two-unit Cincinnati property, with its own lease, household record, ledger, utility responsibility, and maintenance history.",
    features: ["Dedicated entry", "Separate utilities", "Updated kitchen", "Natural light", "Shared yard", "Online resident portal"],
    leaseTerm: "12-month lease",
    parking: "One off-street space",
  },
  "otr-triplex-unit-3": {
    coordinates: { lat: 39.111, lng: -84.515 },
    gallery: [IMAGES.triplex, IMAGES.mixedUse, IMAGES.skyline],
    overview: "A top-floor unit within a three-residence building, balancing historic material character with clearly documented modern operating systems.",
    features: ["Exposed brick", "Top-floor light", "Updated systems", "Water included", "Controlled entry", "Online resident portal"],
    leaseTerm: "12-month lease",
    parking: "Street and nearby garage options",
  },
  "412-elm-commercial-c1": {
    coordinates: { lat: 39.1031, lng: -84.512 },
    gallery: [IMAGES.bakery, IMAGES.storefront, IMAGES.mixedUse],
    overview: "A ground-floor commercial unit within a mixed-use asset, managed independently from the residences above with commercial lease terms, access controls, utilities, maintenance, and compliance records.",
    features: ["Grease trap", "Three-phase power", "Rear loading access", "Storefront glazing", "Separate metering", "Dedicated commercial ledger"],
    leaseTerm: "Commercial term subject to negotiation",
    parking: "Loading and service access included",
  },
};