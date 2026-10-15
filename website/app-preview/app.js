/* SAGE app home (phone layout preview). Numbers and replies are examples: nothing is sent anywhere.
   Rules mirrored from the repo: Spark rate (economy/currency.py), spend limits (economy/spend_ladder.py). */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmt(n) { return Number(n).toLocaleString('en-US'); }

  /* ---------------------------------------------------------- example data */
  var NPR_PER_SPARK = 1;
  var wallet = { balance: 1250, earned: 1250, spent: 0 };
  var RANKS = [
    ['Bronze', '#c7803f'], ['Silver', '#cfd6e4'], ['Gold', '#e9b949'], ['Platinum', '#b4dcf2'],
    ['Jade', '#35c88a'], ['Ruby', '#e0314b'], ['Sapphire', '#3a73ff'], ['Emerald', '#19c26b'],
    ['Diamond Sovereign', '#eaf6ff'], ['Black Opal Realm', '#8c9bff'], ['Painite Core', '#ff5a2e'],
    ['Void Matter', '#9150ff'], ['Californium Overlord', '#ffd36b']
  ];
  var evo = { rank: 0, level: 'Mid', progress: 62 };

  var LADDER = [['Bronze', 'Low', 1], ['Bronze', 'Mid', 10], ['Bronze', 'High', 50]];
  var BANDS = [[100, 10], [1000, 5], [10000, 2]];
  var CEILING = 200;
  function spendLimit(balance, life) {
    var reached = null;
    LADDER.forEach(function (r) { if (life >= r[2]) reached = r; });
    if (!reached) return { level: null, locked: 0, limit: 0 };
    var pct = 1;
    for (var i = 0; i < BANDS.length; i++) { if (life <= BANDS[i][0]) { pct = BANDS[i][1]; break; } }
    var pool = Math.max(0, balance - reached[2]);
    return {
      level: reached[0] + ' ' + reached[1],
      locked: Math.min(balance, reached[2]),
      limit: Math.min(pool, Math.floor(life * pct / 100), CEILING)
    };
  }
  var lim = spendLimit(wallet.balance, wallet.earned);

  /* ------------------------------------------------------------------ home */
  function makeDots(el, count) {
    var html = '';
    for (var i = 0; i < count; i++) html += '<i style="--a:' + Math.round(360 / count * i) + 'deg"></i>';
    el.innerHTML = html;
  }
  makeDots($('homeDots'), 14);
  makeDots($('sheetDots'), 10);

  var card = $('evoCard');
  var strip = $('strip');
  strip.innerHTML = RANKS.map(function (r, i) {
    return '<button type="button" class="gem' + (i > evo.rank ? ' locked' : '') + '" data-i="' + i + '" style="--c:' + r[1] +
      '" aria-pressed="' + (i === evo.rank) + '"><i></i><span>' + (i + 1) + ' ' + esc(r[0]) + '</span></button>';
  }).join('');

  function showRank(i) {
    var r = RANKS[i];
    card.style.setProperty('--accent', r[1]);
    $('evoTitle').textContent = 'Evolution ' + String(i + 1).padStart(2, '0') + ': ' + r[0];
    $('evoSub').textContent = i === evo.rank ? 'Your current rank' : i < evo.rank ? 'Reached' : 'Not reached yet';
    Array.prototype.forEach.call(strip.children, function (b) {
      b.setAttribute('aria-pressed', String(Number(b.dataset.i) === i));
    });
  }
  strip.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-i]');
    if (b) showRank(Number(b.dataset.i));
  });
  showRank(evo.rank);
  $('evoLevel').textContent = evo.level;
  $('evoPct').textContent = evo.progress + '% to ' + RANKS[evo.rank + 1][0];
  $('evoBar').style.width = evo.progress + '%';
  $('evoBar').parentNode.setAttribute('aria-valuenow', String(evo.progress));

  $('moneyLevel').textContent = lim.level;
  $('moneyText').textContent = fmt(lim.locked) + ' Spark is locked as savings. SAGE may propose up to ' + fmt(lim.limit) +
    ' Spark in one spend, and you approve every spend.';
  $('balance').textContent = fmt(wallet.balance);
  $('balanceNpr').textContent = '= NPR ' + fmt(wallet.balance * NPR_PER_SPARK);

  function flashCard(id) {
    var el = $(id);
    if (!el) return;
    el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
    el.classList.remove('flash');
    void el.offsetWidth;
    el.classList.add('flash');
  }

  /* ----------------------------------------------------------------- SAGE */
  var sheet = $('sheet'), transcript = $('transcript'), msg = $('msg'), send = $('send');
  var state = $('state'), stateLabel = $('stateLabel');
  var lastOpener = null, busy = false, spokenMode = false;

  function setState(s, label) { state.setAttribute('data-s', s); stateLabel.textContent = label; }
  function openSheet() {
    lastOpener = document.activeElement;
    sheet.hidden = false;
    setState('idle', 'Ask SAGE anything');
    msg.focus();
  }
  function closeSheet() {
    sheet.hidden = true;
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    if (lastOpener && lastOpener.focus) lastOpener.focus();
  }
  $('sageBtn').addEventListener('click', openSheet);
  $('sheetClose').addEventListener('click', closeSheet);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !sheet.hidden) closeSheet(); });
  $('tabHome').addEventListener('click', function () { $('home').scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }); window.scrollTo(0, 0); });

  function addBubble(who, text, html) {
    var el = document.createElement('div');
    el.className = 'bubble ' + who;
    el.textContent = text;
    transcript.appendChild(el);
    if (html) transcript.insertAdjacentHTML('beforeend', html);
    transcript.scrollTop = transcript.scrollHeight;
    return el;
  }

  var ACTION_RE = /\b(run|launch|start)\b.*\b(ad|ads|campaign)\b|\b(spend|pay|post|publish|send|delete|buy)\b/;
  function reply(text) {
    var t = text.toLowerCase();
    if (ACTION_RE.test(t) && !/^(open|show|go to)\b/.test(t)) {
      var m = t.match(/(\d[\d,]*)\s*(spark)?/);
      var amount = m ? Number(m[1].replace(/,/g, '')) : 15;
      var what = /ad|campaign/.test(t) ? 'Run a Meta ad campaign' : /post|publish/.test(t) ? 'Publish a post' : /send/.test(t) ? 'Send a message' : /delete/.test(t) ? 'Delete data' : 'Spend Spark';
      var within = amount > 0 && amount <= lim.limit;
      return {
        text: within ? 'I can prepare that, but I will not do it until you approve.' : 'That is above what I am allowed to propose. Your limit is ' + fmt(lim.limit) + ' Spark per spend.',
        approval: { what: what, amount: amount, within: within }
      };
    }
    if (/spark|balance|wallet|credit|rupee|npr|money|earn/.test(t)) {
      return { text: 'You have ' + fmt(wallet.balance) + ' Spark, worth NPR ' + fmt(wallet.balance * NPR_PER_SPARK) + '. 1 Spark is NPR 1. Cash-out to rupees is not available yet.', focus: 'balanceCard' };
    }
    if (/limit|ladder|money level|tier/.test(t)) {
      return { text: 'Your money level is ' + lim.level + '. I may propose up to ' + fmt(lim.limit) + ' Spark in one spend, and you approve each one.', focus: 'moneyCard' };
    }
    if (/evolution|rank|level/.test(t)) {
      return { text: 'You are on Evolution 01, ' + RANKS[evo.rank][0] + ', at ' + evo.level + ' intensity. You are ' + evo.progress + '% of the way to ' + RANKS[evo.rank + 1][0] + '.', focus: 'evoCard' };
    }
    if (/research|look up|find out|search/.test(t)) {
      return { text: 'Research complete (example). I found 12 sources and verified 7. October to November and March to May are the clearest seasons for most travellers.' };
    }
    if (/task|to-do|todo/.test(t)) {
      return { text: 'You have 4 tasks (example): 1 running, 1 pending, 1 completed and 1 failed. The failed one was blocked by a website, so I can retry or skip it.' };
    }
    if (/project|memory|market|job|learn|course|setting/.test(t)) {
      return { text: 'That screen is part of the full app menu. This preview only shows the home screen and SAGE.' };
    }
    if (/^(hi|hello|hey|namaste)\b/.test(t)) {
      return { text: 'Namaste. What do you want to get done today?' };
    }
    return { text: 'This preview uses scripted replies, so I cannot answer that yet. In the live SAGE it goes to the research and command engine. Try "show my Spark balance", "what is my Evolution rank?" or "run an ad for 15 Spark".' };
  }

  function approvalHtml(a) {
    return '<div class="approval" data-amount="' + a.amount + '"><h4>Approval needed</h4><dl>' +
      '<dt>Action</dt><dd>' + esc(a.what) + '</dd>' +
      '<dt>Cost</dt><dd>' + fmt(a.amount) + ' Spark (NPR ' + fmt(a.amount * NPR_PER_SPARK) + ')</dd>' +
      '<dt>Your limit</dt><dd>' + fmt(lim.limit) + ' Spark per spend</dd></dl>' +
      '<div class="row">' + (a.within ? '<button type="button" class="btn primary" data-act="approve">Approve</button>' : '') +
      '<button type="button" class="btn" data-act="decline">Decline</button></div>' +
      '<p class="fine">Preview only. Approving does not spend anything.</p></div>';
  }
  transcript.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-act],button[data-show]');
    if (!b) return;
    if (b.dataset.show) { closeSheet(); flashCard(b.dataset.show); return; }
    var box = b.closest('.approval');
    box.querySelector('.row').outerHTML = '<p class="fine">' + (b.dataset.act === 'approve'
      ? 'Approved. In the live app the action would run now. Nothing was spent in this preview.' : 'Declined. Nothing happens.') + '</p>';
    setState('idle', 'Ask SAGE anything');
  });

  function speak(text) {
    if (!('speechSynthesis' in window) || !window.SpeechSynthesisUtterance) return;
    try {
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new window.SpeechSynthesisUtterance(text));
    } catch (err) { /* speaking is optional */ }
  }

  function setBusy(v) { busy = v; send.disabled = v || !msg.value.trim(); }
  var toastTimer = null;
  function toast(text, kind) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.className = 'toast show ' + (kind || 'ok');
    t.textContent = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, 3500);
  }
  var bell = document.getElementById('bellBtn');
  if (bell) bell.addEventListener('click', function () { toast('No new notifications.', 'ok'); });

  function ask(text, viaVoice) {
    text = (text || '').trim();
    if (!text || busy) return;
    if (text.length > 500) { toast('That message is too long. Keep it under 500 characters.', 'err'); return; }
    if (sheet.hidden) openSheet();
    spokenMode = !!viaVoice;
    addBubble('you', text);
    msg.value = '';
    setBusy(true);
    setState('thinking', 'Thinking');
    var r = reply(text);
    window.setTimeout(function () {
      var html = r.approval ? approvalHtml(r.approval) : '';
      if (r.focus) html += '<button type="button" class="btn" data-show="' + r.focus + '" style="justify-self:start">Show it on Home</button>';
      addBubble('sage', r.text, html);
      setState(r.approval ? 'idle' : 'success', r.approval ? 'Waiting for your approval' : 'Done');
      if (spokenMode) speak(r.text);
      setBusy(false);
    }, reduceMotion ? 0 : 700);
  }
  msg.addEventListener('input', function () { send.disabled = busy || !msg.value.trim(); });
  $('compose').addEventListener('submit', function (e) { e.preventDefault(); ask(msg.value, false); });
  document.addEventListener('click', function (e) {
    var c = e.target.closest('[data-cmd]');
    if (c) ask(c.dataset.cmd, false);
  });

  /* ---------------------------------------------------------------- voice */
  var recog = null, mic = $('mic');
  mic.addEventListener('click', function () {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (recog) { recog.stop(); return; }
    if (!SR) { setState('idle', 'Voice is not available here. Type your message.'); return; }
    try {
      recog = new SR();
      recog.lang = 'en-US';
      recog.interimResults = false;
      recog.onresult = function (ev) { ask(ev.results[0][0].transcript, true); };
      recog.onerror = function () { setState('idle', 'I could not hear you. Check microphone access or type instead.'); };
      recog.onend = function () { recog = null; mic.setAttribute('aria-pressed', 'false'); if (state.getAttribute('data-s') === 'listening') setState('idle', 'Ask SAGE anything'); };
      recog.start();
      mic.setAttribute('aria-pressed', 'true');
      setState('listening', 'Listening');
    } catch (err) {
      recog = null;
      setState('idle', 'Voice could not start here. Type your message.');
    }
  });
})();
