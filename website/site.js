/* SAGE ONE website behaviour: mobile menu, scroll progress, back to top,
   horizontal scrollers, form messages, clickable contact details, footer year. */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var doc = document.documentElement;
  doc.classList.add('js');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ------------------------------------------------------------------ toast */
  var toastTimer = null;
  function toast(text, kind) {
    var t = $('toast');
    if (!t) return;
    t.className = 'toast show ' + (kind || 'ok');
    t.textContent = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, 4500);
  }

  /* ------------------------------------------------------------- mobile menu */
  var toggle = $('menuToggle'), nav = $('siteNav'), topbar = document.querySelector('.topbar');
  function setMenu(open) {
    if (!toggle || !nav) return;
    topbar.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
  if (toggle && nav) {
    toggle.addEventListener('click', function () { setMenu(toggle.getAttribute('aria-expanded') !== 'true'); });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { setMenu(false); toggle.focus(); }
    });
    document.addEventListener('click', function (e) {
      if (toggle.getAttribute('aria-expanded') === 'true' && !topbar.contains(e.target)) setMenu(false);
    });
    window.addEventListener('resize', function () { if (window.innerWidth > 880) setMenu(false); });
  }

  /* ------------------------------------------- scroll progress + back to top */
  var bar = $('scrollBar'), topBtn = $('toTop'), ticking = false;
  function onScroll() {
    var max = doc.scrollHeight - window.innerHeight;
    var p = max > 0 ? Math.min(1, window.scrollY / max) : 0;
    if (bar) bar.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    if (topBtn) topBtn.hidden = window.scrollY < 700;
    ticking = false;
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
  if (topBtn) topBtn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
  });

  /* ----------------------------------------------------- horizontal scrollers */
  Array.prototype.forEach.call(document.querySelectorAll('.hscroll'), function (box) {
    var track = box.querySelector('.chips'), prev = box.querySelector('[data-dir="-1"]'), next = box.querySelector('[data-dir="1"]');
    function sync() {
      prev.disabled = track.scrollLeft <= 2;
      next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
      box.classList.toggle('can-left', !prev.disabled);
      box.classList.toggle('can-right', !next.disabled);
    }
    function by(dir) { track.scrollBy({ left: dir * track.clientWidth * 0.7, behavior: reduce ? 'auto' : 'smooth' }); }
    prev.addEventListener('click', function () { by(-1); });
    next.addEventListener('click', function () { by(1); });
    track.addEventListener('scroll', sync, { passive: true });
    window.addEventListener('resize', sync);
    track.addEventListener('keydown', function (e) {
      if (e.target !== track) return;
      if (e.key === 'ArrowRight') { by(1); e.preventDefault(); }
      if (e.key === 'ArrowLeft') { by(-1); e.preventDefault(); }
    });
    // Keep the selected rank in view, including when Evolve changes it.
    function centre() {
      var on = track.querySelector('[aria-pressed="true"]');
      if (!on) return;
      track.scrollTo({ left: on.offsetLeft - (track.clientWidth - on.offsetWidth) / 2, behavior: reduce ? 'auto' : 'smooth' });
    }
    new MutationObserver(centre).observe(track, { attributes: true, attributeFilter: ['aria-pressed'], subtree: true });
    sync();
  });

  /* ------------------------------------------------------------ field messages */
  function setMsg(input, text) {
    var m = $(input.id + '-msg');
    if (m) m.textContent = text || '';
    if (text) input.setAttribute('aria-invalid', 'true'); else input.removeAttribute('aria-invalid');
  }
  ['sparkIn', 'nprIn', 'lifeIn', 'balIn', 'askIn'].forEach(function (id) {
    var el = $(id);
    if (!el) return;
    el.addEventListener('input', function () {
      var v = el.value.trim();
      if (v === '') return setMsg(el, 'Enter a number. Empty counts as 0.');
      var n = Number(v);
      if (!isFinite(n) || n < 0) return setMsg(el, 'Use a whole number of 0 or more.');
      if (Math.floor(n) !== n) return setMsg(el, 'Spark uses whole numbers. The decimals are dropped.');
      if (n > 1e12) return setMsg(el, 'That number is too large. The most it uses is 1,000,000,000,000.');
      setMsg(el, '');
    });
  });

  /* ----------------------------------------------------------- contact details */
  var cfg = window.SITE || {};
  var email = String(cfg.email || '').trim();
  var phoneRaw = String(cfg.phone || '').trim();
  var phoneDigits = phoneRaw.replace(/[^\d+]/g, '');
  var okEmail = /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(email);
  var okPhone = /^\+?\d{7,15}$/.test(phoneDigits);
  var phoneText = String(cfg.phoneLabel || '').trim() || phoneRaw;

  function link(el, href, text) { if (!el) return; el.href = href; el.textContent = text; el.hidden = false; }
  if (okEmail || okPhone) {
    var section = $('contact');
    if (section) section.hidden = false;
    Array.prototype.forEach.call(document.querySelectorAll('[data-contact-link]'), function (a) { a.hidden = false; });
    var fc = document.querySelector('[data-foot-contact]');
    if (fc) fc.hidden = false;
  }
  if (okEmail) {
    link($('contactEmail'), 'mailto:' + email, email);
    link($('footEmail'), 'mailto:' + email, email);
    var row = document.querySelector('[data-contact-email-row]'); if (row) row.hidden = false;
    if ($('contactForm')) $('contactForm').hidden = false;
  }
  if (okPhone) {
    link($('contactPhone'), 'tel:' + phoneDigits, phoneText);
    link($('footPhone'), 'tel:' + phoneDigits, phoneText);
    var prow = document.querySelector('[data-contact-phone-row]'); if (prow) prow.hidden = false;
  }

  /* -------------------------------------------------------------- contact form */
  var form = $('contactForm');
  if (form && okEmail) {
    var status = $('contactStatus');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = $('cName'), from = $('cEmail'), msg = $('cMsg'), bad = null;
      status.textContent = ''; status.className = 'form-status';
      var checks = [
        [name, name.value.trim().length < 2, 'Please enter your name.'],
        [from, !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(from.value.trim()), 'Please enter a valid email address.'],
        [msg, msg.value.trim().length < 10, 'Please write at least 10 characters.']
      ];
      checks.forEach(function (c) { setMsg(c[0], c[1] ? c[2] : ''); if (c[1] && !bad) bad = c[0]; });
      if (bad) {
        status.textContent = 'Please fix the highlighted fields and try again.';
        status.className = 'form-status err';
        bad.focus();
        return;
      }
      var body = msg.value.trim() + '\n\nFrom: ' + name.value.trim() + ' <' + from.value.trim() + '>';
      var href = 'mailto:' + email + '?subject=' + encodeURIComponent('SAGE ONE website message from ' + name.value.trim()) + '&body=' + encodeURIComponent(body);
      if (href.length > 1900) {
        status.textContent = 'That message is too long to send this way. Please shorten it.';
        status.className = 'form-status err';
        return;
      }
      window.location.href = href;
      status.textContent = 'Thanks. Your email app should now open with the message ready. Press send there to finish. If nothing opened, write to ' + email + '.';
      status.className = 'form-status ok';
      toast('Message ready in your email app.', 'ok');
      form.reset();
    });
    ['cName', 'cEmail', 'cMsg'].forEach(function (id) {
      $(id).addEventListener('input', function () { setMsg($(id), ''); });
    });
  }

  /* ---------------------------------------------------------------- Evolve toast */
  var evolve = $('evolveBtn');
  if (evolve) evolve.addEventListener('click', function () {
    var t = $('rankTitle');
    setTimeout(function () { if (t) toast('Now showing ' + t.textContent + '.', 'ok'); }, 3700);
  });

  /* ---------------------------------------------------------------- footer year */
  var y = $('year');
  if (y) y.textContent = String(new Date().getFullYear());
})();
