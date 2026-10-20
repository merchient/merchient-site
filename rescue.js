// The rescue form on rescue.html. Without this script the form opens an email to akhil@merchient.com with the subject
// "Rescue". With it: when Merchient's rescue service hands out a form token, the form posts there, screenshots included;
// when the service does not answer, the email opens instead, with the answers filled in.
(function () {
  var form = document.getElementById('rescue-form');
  if (!form || !window.fetch || !window.FormData || !window.AbortController) { return; }
  var api = form.getAttribute('data-api');
  var how = document.getElementById('rescue-how');
  var msg = form.querySelector('.form-msg');
  var button = form.querySelector('button[type="submit"]');
  var trap = document.getElementById('r-hp');
  var token = null;

  function value(id) { return document.getElementById(id).value.trim(); }

  function within(ms) {
    var controller = new AbortController();
    setTimeout(function () { controller.abort(); }, ms);
    return controller.signal;
  }

  function live(on) {
    token = on;
    trap.disabled = !on;
    how.textContent = on
      ? 'Sending posts your answers and screenshots to Merchient’s rescue service (api.merchient.com). If it does not answer, your email app opens instead.'
      : 'Sending opens your email app, addressed to akhil@merchient.com with the subject “Rescue” and your answers filled in. Attach your screenshots there before you send.';
  }

  function ask() {
    fetch(api + '/api/rescue/token', { credentials: 'omit', signal: within(8000) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (b) { live(b && typeof b.form_token === 'string' ? b.form_token : null); })
      .catch(function () { live(null); });
  }

  function mail(note) {
    var platform = document.getElementById('r-platform');
    var body = 'Name: ' + value('r-name') + '\r\nEmail: ' + value('r-email') + '\r\nBrand: ' + value('r-brand') +
      '\r\nStore: ' + value('r-store') + '\r\nWhere it was rejected: ' + platform.options[platform.selectedIndex].text +
      '\r\n\r\nThe ad’s text, or the listing’s title and bullets:\r\n' + value('r-text') +
      '\r\n\r\nThe platform’s notice:\r\n' + value('r-notice') +
      '\r\n\r\nYou may use this rejection, anonymised, to improve Vera: ' + (form.elements.consent.checked ? 'yes' : 'no') +
      '\r\n\r\n(Attach your screenshots to this email.)\r\n';
    msg.textContent = note;
    window.location.href = 'mailto:akhil@merchient.com?subject=Rescue&body=' + encodeURIComponent(body);
  }

  function fileProblem(files) {
    if (files.length > 3) { return 'Send at most 3 screenshots.'; }
    for (var i = 0; i < files.length; i++) {
      if (!/\.(png|jpe?g|pdf)$/i.test(files[i].name)) { return 'Screenshots must be PNG, JPG or PDF files.'; }
      if (files[i].size > 5 * 1024 * 1024) { return 'Each screenshot must be 5 MB or less.'; }
    }
    return '';
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var files = document.getElementById('r-files').files;
    var problem = fileProblem(files);
    if (problem) { msg.textContent = problem; return; }
    if (!token) { mail('Opening your email app. Attach your screenshots there before you send.'); return; }
    if (!value('r-text') && !files.length) { msg.textContent = 'Paste the ad or listing text, or add a screenshot of it.'; return; }
    var data = new FormData(form);
    data.append('form_token', token);
    button.disabled = true;
    msg.textContent = 'Sending…';
    fetch(api + '/rescue', { method: 'POST', body: data, headers: { Accept: 'application/json' }, credentials: 'omit', signal: within(60000) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, ok: r.ok, body: b }; });
      })
      .then(function (x) {
        button.disabled = false;
        var error = x.body.error || {};
        if (x.ok) {
          form.reset();
          msg.textContent = x.body.message || 'Got it. We’ll reply the same day.';
        } else if (x.status < 500 && error.message) {
          msg.textContent = error.message;
          if (error.code === 'form_expired') { ask(); }
        } else {
          throw new Error('status ' + x.status);
        }
      })
      .catch(function () {
        button.disabled = false;
        mail('The rescue service did not answer, so your email app is opening instead. Attach your screenshots there before you send.');
      });
  });

  ask();
}());
