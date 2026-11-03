// The home page's hero: type a website, see its Claims Facts panel. Without this script the page shows the scan form
// that opens the "Free scan request" email (scan.js posts it when it can). With it, the hero asks Merchient's panel
// service for the website's panel and draws it here in the panel's own look. A panel not read yet is queued and
// polled every 10 seconds for up to 4 minutes. When the service is busy or does not answer, the scan form comes back
// with one line saying so. Only the domain is sent; nothing is stored in the page; no cookies, no analytics.
// Site 44: the query is read for two keys only. ?site=brand.com fills the box and asks for the panel once on load (the
// outreach links use it); a site the panel service refuses leaves the plain box, with no error text. ?v=b swaps the
// hero's headline and sentence for the data-b words in the page, when the page has them; v ("a" or "b") goes with the
// panel requests so the app can count scans by variant.
(function () {
  var q = window.URLSearchParams ? new URLSearchParams(window.location.search) : null;
  var siteQuery = q ? (q.get('site') || '') : '';
  var v = q ? (q.get('v') || '').toLowerCase() : '';
  v = v === 'a' || v === 'b' ? v : '';
  if (v === 'b') {
    var swap = document.querySelectorAll('.hero [data-b]');
    for (var i = 0; i < swap.length; i++) { swap[i].textContent = swap[i].getAttribute('data-b'); }
  }
  var form = document.getElementById('hero-form');
  if (!form || !window.fetch || !window.AbortController) { return; }
  var api = form.getAttribute('data-panel');
  var title = document.getElementById('scan-title');
  var input = document.getElementById('hero-website');
  var button = form.querySelector('button[type="submit"]');
  var msg = form.querySelector('.scan-msg');
  var progress = document.getElementById('hero-progress');
  var out = document.getElementById('hero-panel');
  var mailForm = document.getElementById('hero-email');
  var fallback = document.getElementById('scan-fallback');
  var busy = document.getElementById('scan-busy');
  var domain = '';

  title.textContent = 'Claims Facts';
  fallback.hidden = true;
  form.hidden = false;

  function domainOf(v) {
    v = v.trim().toLowerCase().replace(/^[a-z][a-z0-9+.-]*:\/\//, '').split(/[\/?#]/)[0]
      .replace(/:\d+$/, '').replace(/^www\./, '');
    return /^[a-z0-9-]+(\.[a-z0-9-]+)+$/.test(v) ? v : '';
  }

  function call(url, options) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    options.credentials = 'omit';
    options.signal = controller.signal;
    options.headers = options.headers || {};
    options.headers.Accept = 'application/json';
    return fetch(url, options).then(function (r) {
      clearTimeout(timer);
      return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, ok: r.ok, body: b }; });
    }, function (e) { clearTimeout(timer); throw e; });
  }

  function panelOf(b) {
    var p = b && (b.panel || b);
    return p && typeof p.count === 'number' && p.domain ? p : null;
  }

  // 503 (the service busy, or the queue not open yet) keeps the paste's line; anything else says the website could not
  // be read now, because then the service did not say it was busy.
  function busyForm(x) {
    if (!(x && x.status === 503)) { busy.textContent = 'The instant panel can’t read this website right now; ask for the scan by email instead.'; }
    progress.hidden = true;
    form.hidden = true;
    out.hidden = true;
    title.textContent = 'Free scan';
    busy.hidden = false;
    fallback.hidden = false;
    var site = document.getElementById('scan-website');
    if (site && domain) { site.value = domain; }
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  function row(cls, key, small, value) {
    var r = el('div', 'cf-row' + (cls ? ' ' + cls : ''));
    var k = el('span', 'cf-k');
    k.appendChild(el('b', '', key));
    if (small) { k.appendChild(el('small', '', small)); }
    r.appendChild(k);
    r.appendChild(value === null ? el('span', 'cf-v cf-none', 'Not counted*') : el('span', 'cf-v', String(value)));
    return r;
  }

  function render(p) {
    var level = p.level === 'High' || p.level === 'Medium' ? p.level : '';
    var clear = p.state === 'no_findings';
    var rules = (p.rules || []).slice(0, 3);
    progress.hidden = true;
    form.hidden = true;
    out.textContent = '';
    out.appendChild(el('p', 'cf-brand', (p.brand || p.domain) + ' · ' + p.domain));
    out.appendChild(row('cf-meta', 'Pages read', p.pages_read || '', p.pages_count || 1));
    out.appendChild(row('cf-meta', 'Date read', '', p.date_read || ''));
    out.appendChild(el('div', 'bar-xl'));
    var head = el('div', 'cf-row cf-head');
    head.appendChild(el('span', 'cf-legal', 'Risk review, not legal advice.'));
    head.appendChild(el('span', '', 'Lines'));
    out.appendChild(head);
    out.appendChild(row('cf-top', 'Claims read', '', null));
    out.appendChild(row('', 'High risk', 'FDA disease or drug claims, FTC proof claims, Meta policy', level === 'High' ? p.count : clear ? 0 : null));
    out.appendChild(row('', 'Medium', '', level === 'Medium' ? p.count : clear ? 0 : null));
    out.appendChild(row('', 'Fine', '', null));
    out.appendChild(el('div', 'bar-md'));
    out.appendChild(el('div', 'cf-row cf-top cf-label', 'Rules hit most'));
    rules.forEach(function (r) {
      out.appendChild(row('cf-indent', r.name || r.rule, r.authority ? r.rule + ' · ' + r.authority : r.rule, r.count));
    });
    if (rules.length < 3) {
      var none = row('cf-indent', rules.length ? 'No other rule hit in these lines' : 'No rule hit in these lines', '', 0);
      none.lastChild.textContent = 'None';
      none.lastChild.className = 'cf-v cf-none';
      out.appendChild(none);
    }
    out.appendChild(el('div', 'bar-md'));
    var spend = row('cf-top', 'Ad spend riding on High-risk claims', 'Shown once your Meta ad account is connected', 0);
    spend.lastChild.textContent = 'Not measured yet';
    spend.lastChild.className = 'cf-v cf-none';
    out.appendChild(spend);
    out.appendChild(el('div', 'bar-xl'));
    // The footnotes in the app's words (scan_page.panel): what this reading did not count, and what it did not read.
    var uncounted = ['the claims read'].concat(level !== 'Medium' ? ['the medium lines'] : [],
      level !== 'High' ? ['the high-risk lines'] : [], ['the fine lines']);
    var unread = ['ads', 'emails'].concat(/(^|\.)amazon\./.test(p.domain) ? [] : ['Amazon'], ['the site’s other pages']);
    function and(list) { return list.slice(0, -1).join(', ') + ' and ' + list[list.length - 1]; }
    if (!clear) {
      out.appendChild(el('p', 'cf-foot', '* Not counted this time. This reading tallied the ' + (level || 'flagged').toLowerCase() +
        '-risk lines only; ' + and(uncounted) + ' were not counted.'));
    }
    out.appendChild(el('p', 'cf-foot', 'Customer reviews, menus, footers and offer text are left out. Not read this time: ' +
      and(unread) + '.'));
    out.appendChild(el('p', 'cf-ai', 'Vera is an AI employee at Merchient. Risk review, not legal advice.'));
    title.textContent = 'Claims Facts: ' + p.domain;
    out.hidden = false;
    mailForm.hidden = false;
  }

  function poll(url, started) {
    if (Date.now() - started > 240000) { busyForm(); return; }
    setTimeout(function () {
      call(url, { method: 'GET' }).then(function (x) {
        // The app's status: {"state": "queued" | "ready" | "failed"}, the panel under "panel" when ready.
        var p = x.ok && panelOf(x.body);
        var state = (x.body && x.body.state) || '';
        if (p) { render(p); }
        else if (x.ok && state === 'queued') {
          progress.value = Math.min(240, Math.round((Date.now() - started) / 1000));
          poll(url, started);
        } else { busyForm(x); }
      }).catch(function () { busyForm(); });
    }, 10000);
  }

  // v goes with every panel request, and only when the page was opened with ?v=a or ?v=b.
  function withV(body) { if (v) { body.v = v; } return body; }
  var vQuery = v ? '&v=' + v : '';
  var vOnly = v ? '?v=' + v : '';

  function queue() {
    call(api + '/api/panel/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(withV({ website: domain }))
    }).then(function (x) {
      // 503 {"state": "not_yet"} while the queue is closed; 200 with the panel when one turned up meanwhile; 202 queued.
      var p = x.ok && panelOf(x.body);
      var id = x.body && x.body.id;
      if (p) { render(p); return; }
      if (!x.ok || !id || x.body.state !== 'queued') { busyForm(x); return; }
      msg.textContent = 'Reading your page';
      progress.value = 0;
      progress.hidden = false;
      poll(api + '/api/panel/status/' + encodeURIComponent(id) + vOnly, Date.now());
    }).catch(function () { busyForm(); });
  }

  // The plain box: no value, no message, the button back on. For a ?site= the panel service (or this page's own
  // check) refuses.
  function plain() {
    input.value = '';
    msg.textContent = '';
    button.disabled = false;
  }

  function look(fromQuery) {
    button.disabled = true;
    msg.textContent = 'Looking…';
    call(api + '/api/panel?website=' + encodeURIComponent(domain) + vQuery, { method: 'GET' }).then(function (x) {
      var p = x.ok && panelOf(x.body);
      if (p) { render(p); }
      else if (x.status === 404) { queue(); }
      else if (fromQuery && (x.status === 400 || x.status === 422)) { plain(); }
      else { busyForm(x); }
    }).catch(function () { busyForm(); });
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    domain = domainOf(input.value);
    if (!domain) { msg.textContent = 'Type a website, like yourbrand.com.'; return; }
    look(false);
  });

  if (siteQuery) {
    domain = domainOf(siteQuery);
    if (domain) { input.value = domain; look(true); } else { plain(); }
  }

  mailForm.addEventListener('submit', function (event) {
    event.preventDefault();
    var email = document.getElementById('hero-work-email');
    var note = mailForm.querySelector('.scan-msg');
    var send = mailForm.querySelector('button[type="submit"]');
    send.disabled = true;
    note.textContent = 'Sending…';
    call(api + '/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ website: domain, email: email.value.trim(), panel_seen: true })
    }).then(function (x) {
      var error = x.body.error || {};
      send.disabled = false;
      if (x.ok) { note.textContent = x.body.message || 'Check your inbox: open the link we sent to start the scan.'; }
      else if (x.status < 500 && error.message) { note.textContent = error.message; }
      else { throw new Error('status ' + x.status); }
    }).catch(function () {
      send.disabled = false;
      note.textContent = 'The scan service did not answer, so your email app is opening instead.';
      window.location.href = 'mailto:hello@merchient.com?subject=Free%20scan%20request&body=' +
        encodeURIComponent('Website: ' + domain + '\r\nWork email: ' + email.value.trim() + '\r\n');
    });
  });
}());
