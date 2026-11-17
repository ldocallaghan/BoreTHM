// Render the equations that pymdownx.arithmatex marks, with the vendored KaTeX.
(function () {
  function render() {
    document.querySelectorAll('.arithmatex').forEach(function (element) {
      renderMathInElement(element, {
        delimiters: [
          {left: '\\[', right: '\\]', display: true},
          {left: '\\(', right: '\\)', display: false}
        ],
        throwOnError: false
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
