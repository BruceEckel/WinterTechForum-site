// Menu behavior and the theme toggle. The site reads fine without this file.
(function () {
  var nav = document.getElementById("nav");
  var menuButton = document.querySelector(".menu-button");
  var groups = Array.prototype.slice.call(nav.querySelectorAll("details"));

  function closeGroups(except) {
    groups.forEach(function (group) {
      if (group !== except) group.open = false;
    });
  }

  menuButton.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", open);
  });

  groups.forEach(function (group) {
    group.addEventListener("toggle", function () {
      if (group.open) closeGroups(group);
    });
  });

  document.addEventListener("click", function (event) {
    if (!nav.contains(event.target)) closeGroups(null);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeGroups(null);
  });

  document.querySelector(".theme-button").addEventListener("click", function () {
    var root = document.documentElement;
    var dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try {
      localStorage.setItem("theme", root.dataset.theme);
    } catch (e) {}
  });
})();
