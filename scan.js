// The scan box on the home page. Without this script the form opens the "Free scan request" email. With it, the
// box posts the website and work email as JSON to Merchient's scan service and shows the service's answer, word for
// word. When the service does not answer, the email opens instead, with the answers filled in.
(function () {
  var form = document.querySelector('form.scan[data-api]');
  if (!form || !window.fetch || !window.AbortController) { return; }
  var msg = form.querySelector('.scan-msg');
  var button = form.querySelector('button[type="submit"]');
  var website = document.getElementById('scan-website');
  var email = document.getElementById('scan-email');

  function mail(note) {
    msg.textContent = note;
    window.location.href = 'mailto:hello@merchient.com?subject=Free%20scan%20request&body=' +
      encodeURIComponent('Website: ' + website.value.trim() + '\r\nWork email: ' + email.value.trim() + '\r\n');
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
      body: JSON.stringify({ website: website.value.trim(), email: email.value.trim() }),
      credentials: 'omit',
      signal: controller.signal
    }).then(function (r) {
      clearTimeout(timer);
      return r.json().catch(function () { return {}; }).then(function (b) { return { status: r.status, ok: r.ok, body: b }; });
    }).then(function (x) {
      button.disabled = false;
      var error = x.body.error || {};
      if (x.ok) {
        msg.textContent = x.body.message || 'Check your inbox: open the link we sent to start the scan.';
      } else if (x.status < 500 && error.message) {
        msg.textContent = error.message;
      } else {
        throw new Error('status ' + x.status);
      }
    }).catch(function () {
      clearTimeout(timer);
      button.disabled = false;
      mail('The scan service did not answer, so your email app is opening instead.');
    });
  });
}());
