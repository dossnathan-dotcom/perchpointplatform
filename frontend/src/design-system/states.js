export const STATE_CATALOGUE = [
  ["loading", "This view is loading.", "Nothing was saved.", "Wait for the view to finish."],
  ["refreshing", "This view is refreshing.", "Saved records stay as they were.", "Keep working or wait."],
  ["saved", "The change was saved.", "Yes.", "Continue."],
  ["empty", "There is nothing to show yet.", "Nothing was saved.", "Check another section or wait for a later workflow."],
  ["filtered-empty", "Nothing matches these filters.", "Nothing was saved.", "Clear the filters."],
  ["partial", "Only part of this information is available.", "Nothing new was saved.", "Use the records that are shown."],
  ["stale", "This record changed after you opened it.", "Your latest change was not saved.", "Reload the record and try again."],
  ["denied", "You do not have access to this view.", "Nothing was saved.", "Return to your workspace."],
  ["signed-out", "Your preview session is not signed in.", "Nothing was saved.", "Return to the sign-in preview."],
  ["missing", "That record was not found.", "Nothing was saved.", "Return to the previous list."],
  ["unavailable", "This information is unavailable right now.", "Nothing was saved.", "Try again later."],
  ["database-unavailable", "Records are temporarily unavailable.", "Nothing was saved.", "Try again later."],
  ["offline", "This browser is offline.", "Nothing was saved.", "Reconnect and try again."],
  ["rate-limited", "Too many requests were sent.", "Nothing was saved.", "Wait and try again."],
  ["invalid", "Some fields need attention.", "Nothing was saved.", "Correct the listed fields."],
  ["unexpected", "Something went wrong.", "Nothing was saved.", "Try again. If it continues, contact HawkVision."],
  ["disabled", "This workflow is not available yet.", "Nothing was saved.", "Use only the actions that are enabled."],
  ["synthetic", "This is a synthetic preview.", "No production record was changed.", "Treat every record as an example."],
  ["future", "This workflow belongs to a later phase.", "Nothing was saved.", "Do not treat this screen as a completed action."],
].map(([id, happened, saved, next]) => ({ id, happened, saved, next }));

export function stateCopy(id) {
  return STATE_CATALOGUE.find((item) => item.id === id) || null;
}
