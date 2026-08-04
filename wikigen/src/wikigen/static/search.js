(function () {
  "use strict";

  var input = document.getElementById("wikigen-search-input");
  var results = document.getElementById("wikigen-search-results");
  if (!input || !results || typeof WIKIGEN_SEARCH_INDEX === "undefined") {
    return;
  }

  var prefix = document.body.getAttribute("data-root-prefix") || "";

  function snippet(text, terms) {
    var lower = text.toLowerCase();
    var pos = -1;
    for (var i = 0; i < terms.length; i++) {
      var idx = lower.indexOf(terms[i]);
      if (idx !== -1) {
        pos = idx;
        break;
      }
    }
    if (pos === -1) {
      pos = 0;
    }
    var start = Math.max(0, pos - 40);
    var end = Math.min(text.length, pos + 100);
    return (start > 0 ? "…" : "") + text.slice(start, end) + (end < text.length ? "…" : "");
  }

  function matches(entry, terms) {
    var haystack = (entry.title + " " + entry.text + " " + entry.tags.join(" ")).toLowerCase();
    return terms.every(function (term) {
      return haystack.indexOf(term) !== -1;
    });
  }

  function search(terms) {
    return WIKIGEN_SEARCH_INDEX.filter(function (entry) {
      return matches(entry, terms);
    }).slice(0, 30);
  }

  function render(items, terms) {
    results.innerHTML = "";
    if (items.length === 0) {
      results.classList.remove("open");
      return;
    }
    items.forEach(function (entry) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = prefix + entry.url;
      a.textContent = entry.title;
      var p = document.createElement("p");
      p.className = "wikigen-search-snippet";
      p.textContent = snippet(entry.text, terms);
      li.appendChild(a);
      li.appendChild(p);
      results.appendChild(li);
    });
    results.classList.add("open");
  }

  input.addEventListener("input", function () {
    var query = input.value.trim();
    if (!query) {
      results.innerHTML = "";
      results.classList.remove("open");
      return;
    }
    var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
    render(search(terms), terms);
  });

  document.addEventListener("click", function (evt) {
    if (evt.target !== input && !results.contains(evt.target)) {
      results.classList.remove("open");
    }
  });
})();
