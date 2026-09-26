(function themeInit() {
  var internal = /^\/(perchpoint|foundation|reference|design-system)(\/|$)/.test(window.location.pathname);
  var theme = "hawkvision";
  var density = "comfortable";
  try {
    var storedDensity = window.localStorage.getItem("pp-density");
    if (storedDensity === "comfortable" || storedDensity === "compact") density = storedDensity;
    if (internal) {
      var storedTheme = window.localStorage.getItem("pp-theme");
      if (storedTheme !== "light" && storedTheme !== "dark" && storedTheme !== "system") storedTheme = "dark";
      theme = storedTheme;
      if (theme === "system") {
        theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      }
    }
  } catch (error) {
    theme = internal ? "dark" : "hawkvision";
  }
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-density", density);
})();
