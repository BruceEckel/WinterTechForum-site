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
    if (event.key !== "Escape") return;
    closeGroups(null);
    if (nav.classList.contains("open")) {
      nav.classList.remove("open");
      menuButton.setAttribute("aria-expanded", "false");
      menuButton.focus();
    }
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

  // The contact address stays encoded until a visitor asks for it, so a
  // program that reads the page, or runs its scripts on load, finds no address.
  var NAME = [73, 121, 124, 106, 108, 91, 76, 106, 114, 108, 115];
  var HOST = [110, 116, 104, 112, 115, 53, 106, 118, 116];

  function decode(codes) {
    return codes
      .map(function (code) {
        return String.fromCharCode(code - 7);
      })
      .join("");
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".email-button"),
    function (button) {
      button.addEventListener("click", function () {
        var address = decode(NAME) + String.fromCharCode(64) + decode(HOST);
        var link = document.createElement("a");
        link.href = "mai" + "lto:" + address;
        link.textContent = address;
        button.replaceWith(link);
        link.focus();
      });
    }
  );
})();
