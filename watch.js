// The Claims Watch box on claims-watch.html. Without this script the form opens an email to hello@merchient.com with
// the subject "Claims Watch". With it, the box posts the address as JSON to Merchient's list service and shows the
// service's answer, word for word. When the service does not answer, the email opens instead.
(function () {
  var form = document.getElementById('watch-form');
  if (!form || !window.fetch || !window.AbortController) { return; }
  var msg = form.querySelector('.scan-msg');
  var button = form.querySelector('button[type="submit"]');
  var email = document.getElementById('cw-email');

  function mail(note) {
    msg.textContent = note;
    window.location.href = 'mailto:hello@merchient.com?subject=Claims%20Watch&body=' +
      encodeURIComponent('Please send Claims Watch to: ' + email.value.trim() + '\r\n');
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, 10000);
    button.disabled = true;
    msg.textContent = 'Sending…';
    fetch(form.getAttribute('data-api'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ email: email.value.trim() }),
      credentials: 'omit',
      signal: controller.signal
    }).then(function (r) {
      clearTimeout(timer);
      return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, ok: r.ok, body: b }; });
    }).then(function (x) {
      button.disabled = false;
      var error = x.body.error || {};
      if (x.ok) {
        msg.textContent = x.body.message || 'Check your inbox: open the link we sent to join.';
      } else if (x.status < 500 && error.message) {
        msg.textContent = error.message;
      } else {
        throw new Error('status ' + x.status);
      }
    }).catch(function () {
      clearTimeout(timer);
      button.disabled = false;
      mail('The list service did not answer, so your email app is opening instead.');
    });
  });
}());
