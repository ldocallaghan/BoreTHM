// Open and close the navigation panel on narrow windows.
(function () {
  var toggle = document.querySelector('[data-nav-toggle]');
  var nav = document.getElementById('site-nav');
  if (!toggle || !nav) {
    return;
  }
  function isOpen() {
    return document.body.classList.contains('nav-open');
  }
  function setOpen(open) {
    document.body.classList.toggle('nav-open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  toggle.addEventListener('click', function () {
    setOpen(!isOpen());
    if (isOpen()) {
      var link = nav.querySelector('.nav-link.active') || nav.querySelector('a');
      if (link) {
        link.focus();
      }
    }
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isOpen()) {
      setOpen(false);
      toggle.focus();
    }
  });
  document.addEventListener('click', function (event) {
    if (isOpen() && !nav.contains(event.target) && !toggle.contains(event.target)) {
      setOpen(false);
    }
  });
  window.matchMedia('(min-width: 761px)').addEventListener('change', function (query) {
    if (query.matches) {
      setOpen(false);
    }
  });
})();
