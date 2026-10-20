/* CampusFlow UI enhancements: dark mode, mobile nav, back-to-top, password toggle, copy buttons, loading */
(function () {
  var root = document.documentElement;
  var ICON = {
    sun: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>',
    menu: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    close: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    up: '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>',
    eye: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    eyeOff: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.9 17.9A10.4 10.4 0 0 1 12 19C5.6 19 2 12 2 12a18 18 0 0 1 4.1-5M9.9 5.2A9.7 9.7 0 0 1 12 5c6.4 0 10 7 10 7a18 18 0 0 1-2.2 3.2M1 1l22 22M9.9 9.9a3 3 0 0 0 4.2 4.2"/></svg>',
    copy: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    check: '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>'
  };

  /* ---------- Theme (runs immediately to avoid a flash) ---------- */
  var theme = null;
  try { theme = localStorage.getItem('theme'); } catch (e) {}
  if (!theme) theme = (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  root.setAttribute('data-theme', theme);

  function applyTheme(t) {
    root.setAttribute('data-theme', t);
    try { localStorage.setItem('theme', t); } catch (e) {}
    var m = document.querySelector('meta[name=theme-color]');
    if (m) m.content = t === 'dark' ? '#141829' : '#eef1fb';
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
    // Fallback for http://192.168.x.x on a phone (clipboard API needs HTTPS)
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text; ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0';
      document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0, text.length);
      try { document.execCommand('copy') ? resolve() : reject(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    applyTheme(root.getAttribute('data-theme'));

    /* ---------- Progress bar + toast ---------- */
    var progress = document.createElement('div');
    progress.id = 'progress'; progress.setAttribute('aria-hidden', 'true');
    document.body.appendChild(progress);
    var progressTimer;
    function startProgress() {
      progress.classList.add('run');
      clearTimeout(progressTimer);
      progressTimer = setTimeout(stopProgress, 10000); // safety net (e.g. file downloads)
    }
    function stopProgress() { progress.classList.remove('run'); }
    window.addEventListener('pageshow', function () {
      stopProgress();
      document.querySelectorAll('.loading').forEach(function (b) { b.classList.remove('loading'); });
    });

    var toast = document.createElement('div');
    toast.id = 'toast'; toast.setAttribute('role', 'status');
    document.body.appendChild(toast);
    var toastTimer;
    function showToast(msg) {
      toast.textContent = msg; toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 1800);
    }

    /* ---------- Header: theme toggle + mobile menu ---------- */
    var bar = document.querySelector('.topbar');
    if (bar) {
      var nav = bar.querySelector('nav');
      var actions = document.createElement('div');
      actions.className = 'top-actions';
      if (nav) actions.appendChild(nav);

      var themeBtn = document.createElement('button');
      themeBtn.type = 'button'; themeBtn.id = 'theme-toggle'; themeBtn.className = 'icon-btn';
      themeBtn.setAttribute('aria-label', 'Toggle dark mode'); themeBtn.title = 'Toggle dark mode';
      themeBtn.innerHTML = '<span class="ico-sun">' + ICON.sun + '</span><span class="ico-moon">' + ICON.moon + '</span>';
      themeBtn.addEventListener('click', function () {
        applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
      });
      actions.appendChild(themeBtn);

      if (nav) {
        var menuBtn = document.createElement('button');
        menuBtn.type = 'button'; menuBtn.className = 'icon-btn nav-toggle';
        menuBtn.setAttribute('aria-label', 'Open menu'); menuBtn.setAttribute('aria-expanded', 'false');
        menuBtn.innerHTML = ICON.menu;
        menuBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          var open = nav.classList.toggle('open');
          menuBtn.innerHTML = open ? ICON.close : ICON.menu;
          menuBtn.setAttribute('aria-expanded', open);
        });
        document.addEventListener('click', function (e) {
          if (nav.classList.contains('open') && !nav.contains(e.target)) {
            nav.classList.remove('open'); menuBtn.innerHTML = ICON.menu; menuBtn.setAttribute('aria-expanded', 'false');
          }
        });
        actions.appendChild(menuBtn);
      }
      bar.appendChild(actions);
    }

    /* ---------- Back to top ---------- */
    var top = document.createElement('button');
    top.type = 'button'; top.className = 'to-top'; top.setAttribute('aria-label', 'Back to top');
    top.innerHTML = ICON.up;
    top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    document.body.appendChild(top);
    function onScroll() { top.classList.toggle('show', window.scrollY > 300); }
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

    /* ---------- Password visibility toggle ---------- */
    document.querySelectorAll('input[type=password]').forEach(function (input) {
      var wrap = document.createElement('div');
      wrap.className = 'pw-wrap';
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'pw-toggle'; b.setAttribute('aria-label', 'Show password');
      b.innerHTML = ICON.eye;
      b.addEventListener('click', function () {
        var show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        b.innerHTML = show ? ICON.eyeOff : ICON.eye;
        b.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      });
      wrap.appendChild(b);
    });

    /* ---------- Copy buttons ---------- */
    function makeCopyBtn(text, label) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'copy-btn';
      b.innerHTML = ICON.copy + (label ? '<span>' + label + '</span>' : '');
      b.setAttribute('aria-label', 'Copy ' + (label || text));
      b.addEventListener('click', function () {
        copyText(text).then(function () {
          b.classList.add('done'); var old = b.innerHTML;
          b.innerHTML = ICON.check + (label ? '<span>Copied</span>' : '');
          showToast('Copied to clipboard');
          setTimeout(function () { b.classList.remove('done'); b.innerHTML = old; }, 1500);
        }, function () { showToast('Copy failed - select the text manually'); });
      });
      return b;
    }
    // Any element with data-copy="value" gets a copy icon after it
    document.querySelectorAll('[data-copy]').forEach(function (el) {
      el.insertAdjacentElement('afterend', makeCopyBtn(el.getAttribute('data-copy')));
    });
    // Flash messages containing "Initial password: XYZ" get a "Copy password" button
    document.querySelectorAll('.flash').forEach(function (f) {
      var m = f.textContent.match(/Initial password:\s*(\S+)/);
      if (m) { f.classList.add('flash-copy'); f.appendChild(makeCopyBtn(m[1].replace(/[.,;]+$/, ''), 'Copy password')); }
    });

    /* ---------- Loading animation on navigation / form submit ---------- */
    document.addEventListener('submit', function (e) {
      if (e.defaultPrevented) return;
      var btn = e.submitter || e.target.querySelector('button[type=submit], button:not([type])');
      startProgress();
      if (btn) setTimeout(function () { btn.classList.add('loading'); }, 0);
    });
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href]');
      if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
      var href = a.getAttribute('href');
      if (!href || href.charAt(0) === '#' || a.target === '_blank' || a.hasAttribute('download') ||
          href.indexOf('/uploads/') === 0 || a.origin !== location.origin) return;
      startProgress();
    });
  });
})();
