export const PORTAL_VIEWS = {
  owner: {
    label: "Owner command view",
    tabs: ["Portfolio", "Reserved approvals", "Financials", "Delegations", "Audit"],
    metrics: [["Occupied units", "8 of 10"], ["Open approvals", "3"], ["Rent posted", "$18,940"], ["Priority work", "2"]],
    tasks: [["Lease decision", "412-A applicant package", "Owner reserved"], ["Repair authorization", "Clifton B · plumbing", "Above unit rent"], ["Budget variance", "412 Elm · roof HVAC", "Review"]],
  },
  "super-admin": {
    label: "Platform administration",
    tabs: ["System health", "Roles", "Policy engine", "Security", "Audit trails"],
    metrics: [["Services", "Staging only"], ["Role templates", "8"], ["Policy rules", "6 draft"], ["Open security items", "2"]],
    tasks: [["Identity provider", "Awaiting Phase 0 decision", "Blocked"], ["Data retention", "Contract definition required", "Draft"], ["Role policy", "Owner vs. infrastructure split", "Defined"]],
  },
  leasing: {
    label: "Leasing operations",
    tabs: ["Inquiries", "Showings", "Applications", "Leases", "Turnover"],
    metrics: [["New inquiries", "7"], ["Showings this week", "4"], ["Applications", "3"], ["Units turning", "2"]],
    tasks: [["Showing", "412-A · Tuesday 4:30 PM", "Confirmed"], ["Application", "Clifton B · income verification", "Waiting"], ["Turnover", "OTR Unit 3 · paint scope", "In progress"]],
  },
  accounting: {
    label: "Accounting workspace",
    tabs: ["Collections", "Invoices", "Ledgers", "Reconciliation", "Reports"],
    metrics: [["Rent collected", "$18,940"], ["Open invoices", "5"], ["Unreconciled", "3"], ["Owner packets", "1 due"]],
    tasks: [["Deposit", "412-A holding deposit", "Review"], ["Invoice", "HVAC vendor · 412 Elm", "Approved"], ["Reconciliation", "Operating account · June", "In progress"]],
  },
  maintenance: {
    label: "Maintenance dispatch",
    tabs: ["Assigned work", "Schedule", "Parts", "Evidence", "Completed"],
    metrics: [["Assigned today", "4"], ["Emergency", "1"], ["Waiting parts", "2"], ["Due this week", "6"]],
    tasks: [["PP-1042", "Active leak · Clifton B", "Emergency"], ["PP-1038", "412 Elm hallway light", "Scheduled"], ["PP-1029", "OTR Unit 3 turnover photos", "Due today"]],
  },
  subcontractor: {
    label: "Assigned vendor work",
    tabs: ["Assigned jobs", "Estimates", "Site access", "Evidence", "Invoices"],
    metrics: [["Active jobs", "2"], ["Estimate due", "1"], ["Approved access", "1"], ["Invoices pending", "1"]],
    tasks: [["PP-1040", "412 Elm rooftop HVAC", "Estimate due"], ["PP-1034", "Clifton furnace inspection", "Access approved"], ["Invoice 207", "Completed condenser repair", "Submitted"]],
  },
  resident: {
    label: "Your PerchPoint Resident Portal",
    tabs: ["Home", "Balance & pay", "Lease", "Maintenance", "Building access"],
    metrics: [["Current balance", "$0"], ["Next rent", "$2,250"], ["Lease ends", "May 2027"], ["Open requests", "1"]],
    tasks: [["Rent", "Next payment due July 1", "Scheduled"], ["Maintenance", "Kitchen faucet follow-up", "Assigned"], ["Document", "Renewal notice", "New"]],
  },
  applicant: {
    label: "Application workspace",
    tabs: ["Status", "Documents", "Screening consent", "Messages", "Next steps"],
    metrics: [["Application", "In review"], ["Documents", "4 of 5"], ["Consent", "Complete"], ["Target unit", "412-A"]],
    tasks: [["Income verification", "Most recent pay statement", "Needed"], ["Screening", "Consent received", "Complete"], ["Decision", "Owner review after verification", "Pending"]],
  },
};

export const DELEGATION_RULES = [
  ["Routine purchase", "Within property budget + staff limit", "Assigned staff", "Receipt required"],
  ["Parts above $500", "Configurable threshold", "Manager or owner", "Budget check"],
  ["Repair above monthly rent", "Total issue cost", "Farouk", "Hard approval stop"],
  ["Outside approved budget", "Any category", "Manager or Farouk", "Variance reason"],
  ["Lease or final applicant approval", "Reserved decision", "Farouk", "Permanent audit event"],
  ["Life/property emergency", "Emergency flag + evidence", "Emergency authority", "Immediate notice + review"],
];