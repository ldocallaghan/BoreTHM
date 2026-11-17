// Show the results list under the search box while a query is entered.
// MkDocs' search plugin (search/main.js) runs the search and fills the list.
(function () {
  var box = document.querySelector('[data-search]');
  var input = document.getElementById('mkdocs-search-query');
  var results = document.getElementById('mkdocs-search-results');
  if (!box || !input || !results) {
    return;
  }
  function update() {
    results.hidden = input.value.trim().length < 3;
  }
  input.addEventListener('input', update);
  input.addEventListener('focus', update);
  new MutationObserver(update).observe(results, {childList: true});
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      input.value = '';
      results.hidden = true;
    } else if (event.key === 'ArrowDown') {
      var first = results.querySelector('a');
      if (first) {
        event.preventDefault();
        first.focus();
      }
    }
  });
  box.addEventListener('focusout', function () {
    window.setTimeout(function () {
      if (!box.contains(document.activeElement)) {
        results.hidden = true;
      }
    }, 0);
  });
  document.addEventListener('click', function (event) {
    if (!box.contains(event.target)) {
      results.hidden = true;
    }
  });
  document.addEventListener('keydown', function (event) {
    var typing = /^(input|textarea|select)$/i.test(document.activeElement.tagName);
    if (event.key === '/' && !typing) {
      event.preventDefault();
      input.focus();
    }
  });
})();
