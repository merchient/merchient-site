// The configurator (site 51): "Your price in 20 seconds", on the home page and /pricing. No network call, no storage,
// no email asked before the price. build.py writes the block from content 44's words: three questions, and one result
// card per answer to the first (its price is in the page, never in this file). Q1 picks the card; Q2 and Q3 change the
// words (the Q3 line) and the email, never the price. Start my audit opens the band's checkout URL when
// config/links.json has one (build.py puts it in data-checkout-<band>), else an email to hello@merchient.com carrying
// the three answers. The agency card books the 15-minute call (data-call). Without this script every card shows.
// tools/configurator_selftest.py runs band(), mailto() and links() in Node against a table of answers.
(function () {
  'use strict';
  var BANDS = ['up-to-25', '26-100', 'over-100', 'agency'];

  // a: the answers' values, {q1, q2, q3}. The card to show, or null while Q1 is not answered.
  function band(a) { return a && BANDS.indexOf(a.q1) !== -1 ? a.q1 : null; }

  // say: the answers' words, {value: Q1's value, q1, q2, q3}; '' for a question not answered.
  function mailto(to, say) {
    var subject = 'My audit: ' + (say.value === 'agency' ? say.q1 : say.q1 + ' live ads');
    var line = function (k, v) { return v ? k + v + '.' : k; };
    var body = ['Website: ', line('Live ads: ', say.q1), line('Pages: ', say.q2),
      line('A rejection or restriction in the last 90 days: ', say.q3)].join('\r\n');
    return 'mailto:' + to + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  }

  // cfg: {checkout: {band: url}, call: url, mail: address}. {start, soft}: the card's button and its soft line.
  function links(a, say, cfg) {
    var b = band(a);
    if (!b) { return null; }
    var mail = mailto(cfg.mail, say);
    if (b === 'agency') { return { start: cfg.call || mail, soft: mail }; }
    return { start: (cfg.checkout && cfg.checkout[b]) || mail, soft: cfg.call || mail };
  }

  var api = { band: band, mailto: mailto, links: links };
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  if (typeof document === 'undefined') { return; }

  var box = document.getElementById('cfg');
  if (!box) { return; }
  var cfg = { checkout: {}, call: box.getAttribute('data-call') || '', mail: box.getAttribute('data-mail') };
  for (var i = 0; i < 3; i++) { cfg.checkout[BANDS[i]] = box.getAttribute('data-checkout-' + BANDS[i]) || ''; }
  var cards = box.querySelectorAll('.cfg-card');
  var fair = box.querySelector('.cfg-fair');

  function answers() {
    var a = {}, say = {};
    ['q1', 'q2', 'q3'].forEach(function (q) {
      var on = box.querySelector('input[name="' + q + '"]:checked');
      a[q] = on ? on.value : '';
      say[q] = on ? on.getAttribute('data-say') : '';
    });
    say.value = a.q1;
    return { a: a, say: say };
  }

  function draw() {
    var x = answers(), b = band(x.a);
    for (var i = 0; i < cards.length; i++) { cards[i].hidden = cards[i].getAttribute('data-band') !== b; }
    if (fair) { fair.hidden = !b; }
    if (!b) { return; }
    var card = box.querySelector('.cfg-card[data-band="' + b + '"]');
    var q3 = card.querySelectorAll('.cfg-q3');
    for (var j = 0; j < q3.length; j++) { q3[j].hidden = q3[j].getAttribute('data-q3') !== x.a.q3; }
    var l = links(x.a, x.say, cfg);
    card.querySelector('.cfg-start').setAttribute('href', l.start);
    var soft = card.querySelector('.cfg-call a');
    if (soft) { soft.setAttribute('href', l.soft); }
  }

  box.addEventListener('change', draw);
  draw();
})();
