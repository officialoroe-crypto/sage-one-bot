/* SAGE phone home. Real data only: rank, Spark and tasks come from the SAGE server; the SAGE button
   sends your typed or spoken words to the server and shows the real answer. */
(function () {
  'use strict';
  var S = window.SAGE;
  var esc = S.esc, fmt = S.fmt, toast = S.toast;
  var $ = function (id) { return document.getElementById(id); };
  var COLORS = { Bronze: '#c7803f', Silver: '#cfd6e4', Gold: '#e9b949', Platinum: '#b4dcf2', Jade: '#35c88a', Ruby: '#e0314b', Sapphire: '#3a73ff', Emerald: '#19c26b', 'Diamond Sovereign': '#eaf6ff', 'Black Opal Realm': '#8c9bff', 'Painite Core': '#ff5a2e', 'Void Matter': '#9150ff', 'Californium Overlord': '#ffd36b' };
  var st = { sessionId: null, taskId: null, handle: null, busy: false, mode: 'chat', spoken: false, rec: null };

  /* orbit dots */
  function dots(el, n) { var h = ''; for (var i = 0; i < n; i++) h += '<i style="--a:' + (360 / n * i) + 'deg"></i>'; el.innerHTML = h; }
  dots($('homeDots'), 13); dots($('sheetDots'), 13);

  /* ---------------------------------------------------------- sign-in gate */
  function gateMsg(t) { var m = $('gateMsg'); m.textContent = t || ''; m.hidden = !t; }
  function gateStatus(t, ok) { var s = $('gateStatus'); s.textContent = t; s.className = 'status ' + (ok === true ? 'ok' : ok === false ? 'bad' : ''); }
  function bootGate(reason) {
    $('gate').hidden = false; $('devBtn').hidden = true; $('retryBtn').hidden = true; $('googleSlot').innerHTML = '';
    gateMsg(reason === 'expired' ? 'Your sign-in ended. Please sign in again.' : '');
    gateStatus('Connecting to the SAGE server...');
    if (!S.base) { gateStatus('The SAGE server address is not set. Add apiBase to site-config.js.', false); return; }
    S.api('GET', '/identity/config', null, { noAuth: true, timeout: 70000 }).then(function (cfg) {
      gateStatus('Connected to the SAGE server.', true);
      if (cfg.google_client_id) {
        S.renderGoogleButton($('googleSlot'), cfg.google_client_id, function (cred) {
          gateMsg(''); gateStatus('Signing you in...');
          S.loginWithGoogleCredential(cred).then(enter).catch(function (err) {
            gateStatus('Connected to the SAGE server.', true);
            gateMsg(err.status === 403 ? 'This SAGE server is private and this Google account is not its owner.' : err.message);
          });
        }).catch(function () { gateMsg('Google sign-in could not load. A browser extension or network filter may be blocking accounts.google.com.'); $('retryBtn').hidden = false; });
      } else if (!cfg.developer_mode) {
        gateMsg('Google sign-in is not set up on the SAGE server yet. The server owner needs to set GOOGLE_CLIENT_ID.');
      }
      if (cfg.developer_mode) $('devBtn').hidden = false;
    }, function (err) { gateStatus(err.message, false); $('retryBtn').hidden = false; });
  }
  $('retryBtn').addEventListener('click', function () { bootGate(); });
  $('devBtn').addEventListener('click', function () {
    gateMsg('');
    S.loginDeveloper('web-owner').then(enter).catch(function (err) {
      gateMsg(err.status === 403 || err.status === 404 ? 'Developer sign-in only works when this page and the server are on the same computer.' : err.message);
    });
  });
  S.on('signedout', function (info) { closeSheet(); bootGate(info && info.reason); });
  $('avatar').addEventListener('click', function () { if (window.confirm('Sign out of SAGE on this device?')) S.signOut(); });

  /* ------------------------------------------------------------- home data */
  function enter() {
    $('gate').hidden = true;
    return Promise.all([
      S.api('GET', '/identity/me'), S.api('GET', '/economy/me'),
      S.api('GET', '/economy/evolution/tiers'), S.api('GET', '/economy/spend-limit')
    ]).then(function (r) {
      var p = r[0].profile || {}, eco = r[1], tiers = r[2].tiers || [], lim = r[3].spend_limit || {};
      var name = p.name || (p.email ? p.email.split('@')[0] : '');
      $('avatar').textContent = (name || '?').charAt(0).toUpperCase();
      $('hello').textContent = name ? 'Welcome back, ' + name.split(' ')[0] + '. What do we get done today?' : 'Welcome back. What do we get done today?';
      $('setupNote').hidden = !!p.onboarding_completed;
      var evo = eco.evolution, ratio = Math.max(0, Math.min(1, (evo.progress && evo.progress.ratio) || 0)), pct = Math.round(ratio * 100);
      var next = evo.progress && evo.progress.next_tier;
      $('evoTitle').textContent = 'Evolution: ' + evo.tier;
      $('evoLevel').textContent = String(evo.stage || '').toLowerCase() || '-';
      $('evoPct').textContent = next ? pct + '% to ' + next : 'Final Evolution';
      $('evoBar').style.width = pct + '%';
      $('evoBar').parentNode.setAttribute('aria-valuenow', pct);
      var strip = $('strip'); strip.innerHTML = '';
      var reached = true;
      tiers.forEach(function (t) {
        var b = document.createElement('button'); b.type = 'button';
        var current = t.tier === evo.tier; var locked = !current && !reached;
        if (current) reached = false;
        b.className = 'gem' + (locked || (!current && !reached) ? ' locked' : '');
        b.style.setProperty('--c', COLORS[t.tier] || '#7aa8ff');
        b.setAttribute('aria-pressed', current ? 'true' : 'false');
        b.innerHTML = '<i></i><span>' + esc(t.tier) + '</span><small class="num">' + fmt(t.threshold) + '</small>';
        strip.appendChild(b);
      });
      var on = strip.querySelector('[aria-pressed="true"]'); if (on && on.scrollIntoView) { try { strip.scrollLeft = on.offsetLeft - 24; } catch (e) { /* ignore */ } }
      $('moneyLevel').textContent = lim.level || 'None yet';
      $('moneyText').textContent = lim.note || '';
      var sp = eco.spark;
      $('balance').textContent = fmt(sp.balance);
      $('balanceNpr').textContent = '= NPR ' + fmt(sp.npr_value);
      $('earned').textContent = 'Earned ' + fmt(sp.lifetime_earned);
      $('spent').textContent = 'Spent ' + fmt(sp.lifetime_spent);
      $('spBal').textContent = fmt((eco.points || {}).balance || 0) + ' SP';
    }).catch(function (err) { if (err.status !== 401) toast(err.message, 'err'); });
  }

  /* ------------------------------------------------------------- the sheet */
  var sheet = $('sheet'), transcript = $('transcript'), msg = $('msg'), send = $('send');
  function setState(s, label) { $('state').dataset.s = s; $('stateLabel').textContent = label || ''; }
  function addBubble(cls, html) { var d = document.createElement('div'); d.className = 'bubble ' + cls; d.innerHTML = html; transcript.appendChild(d); transcript.scrollTop = transcript.scrollHeight; return d; }
  function openSheet(mode, prefill) {
    st.mode = mode; sheet.hidden = false; $('sheetTitle').textContent = mode === 'tasks' ? 'Your tasks' : 'SAGE';
    $('compose').hidden = mode === 'tasks'; $('state').hidden = mode === 'tasks';
    if (mode === 'tasks') { loadTasks(); return; }
    setState('idle', 'Ask SAGE anything');
    if (prefill) msg.value = prefill; send.disabled = !msg.value.trim();
    setTimeout(function () { msg.focus(); }, 50);
  }
  function closeSheet() { S.voice.stopListening(); S.voice.stopSpeaking(); sheet.hidden = true; }
  $('sheetClose').addEventListener('click', closeSheet);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !sheet.hidden) closeSheet(); });
  $('sageBtn').addEventListener('click', function () { openSheet('chat'); });
  $('tabResearch').addEventListener('click', function () { openSheet('chat', 'Research '); });
  $('tabTasks').addEventListener('click', function () { openSheet('tasks'); });
  $('tabWallet').addEventListener('click', function () { var c = $('balanceCard'); c.scrollIntoView({ behavior: 'smooth', block: 'center' }); c.classList.remove('flash'); void c.offsetWidth; c.classList.add('flash'); });
  $('tabHome').addEventListener('click', function () { closeSheet(); $('home').scrollTo ? $('home').scrollTo({ top: 0, behavior: 'smooth' }) : window.scrollTo(0, 0); });
  msg.addEventListener('input', function () { send.disabled = st.busy || !msg.value.trim(); });

  function loadTasks() {
    transcript.innerHTML = '<p class="muted">Loading your tasks...</p>';
    S.api('GET', '/tasks').then(function (r) {
      var items = (r.tasks || []).slice(0, 30);
      transcript.innerHTML = items.length ? '<ul class="tasks-list">' + items.map(function (t) {
        return '<li><b>' + esc(t.title || t.description || 'Task') + '</b><small>' + esc(t.status) + ' · ' + esc(S.relTime(t.created_at)) + '</small></li>';
      }).join('') + '</ul>' : '<p class="muted">No tasks yet. Ask SAGE to do something and it will appear here.</p>';
    }, function (err) { transcript.innerHTML = '<p class="muted">' + esc(err.message) + '</p>'; });
  }

  var V = S.voice;
  function speak(text) { V.speak(text); }
  function ask(text, viaVoice) {
    if (st.busy || !text.trim()) return;
    st.busy = true; send.disabled = true; $('stopBtn').hidden = false;
    addBubble('you', esc(text)); msg.value = '';
    setState('thinking', 'SAGE is working on it...');
    var pending = addBubble('sage', '<span class="muted">Working on it...</span>');
    st.handle = S.sendCommand(text, {
      sessionId: st.sessionId,
      onQueued: function (q) { st.sessionId = q.sessionId; st.taskId = q.task && q.task.id; },
      onStatus: function (t) { if (t.status === 'running') setState('thinking', 'SAGE is working on it...'); }
    });
    st.handle.promise.then(function (r) {
      st.sessionId = r.sessionId; pending.innerHTML = S.md(r.text); setState('success', 'Done'); if (viaVoice && V.speak(r.text, function () { $('hushBtn').hidden = true; })) $('hushBtn').hidden = false;
      loadHomeQuiet();
    }, function (err) {
      pending.className = 'bubble sage error'; pending.textContent = err.message || 'SAGE could not finish that.'; setState('idle', 'Something went wrong');
    }).then(function () { st.busy = false; st.handle = null; $('stopBtn').hidden = true; send.disabled = !msg.value.trim(); transcript.scrollTop = transcript.scrollHeight; });
  }
  function loadHomeQuiet() { S.api('GET', '/economy/me').then(function (eco) { $('balance').textContent = fmt(eco.spark.balance); }, function () {}); }
  $('compose').addEventListener('submit', function (e) { e.preventDefault(); ask(msg.value, false); });
  $('stopBtn').addEventListener('click', function () {
    if (!st.handle) return; st.handle.cancel();
    if (st.taskId) S.api('POST', '/tasks/' + encodeURIComponent(st.taskId) + '/cancel').catch(function () {});
  });

  /* voice in: shared SAGE.voice (browser speech recognition) */
  var mic = $('mic'), langBtn = $('langBtn');
  function paintLang() { langBtn.textContent = V.lang() === 'ne' ? 'ने' : 'EN'; langBtn.setAttribute('aria-label', 'Voice language: ' + V.langLabel() + '. Tap to switch.'); }
  paintLang();
  langBtn.addEventListener('click', function () {
    V.toggleLang(); paintLang();
    setState('idle', 'Voice language: ' + V.langLabel() + (V.lang() === 'ne' && V.canSpeak && !V.hasVoiceForLang() ? ' (no Nepali voice on this device for replies)' : ''));
  });
  if (V.canListen) mic.hidden = false;
  mic.addEventListener('click', function () {
    if (V.listening()) { V.stopListening(); return; }
    V.stopSpeaking(); $('hushBtn').hidden = true;
    var ok = V.listen({
      onText: function (interim, final) { msg.value = (final + interim).trim(); send.disabled = st.busy || !msg.value.trim(); },
      onError: function (code) { setState('idle', V.errorText(code)); },
      onEnd: function (finalText) {
        mic.setAttribute('aria-pressed', 'false');
        if (finalText) ask(finalText, true); else if ($('state').dataset.s === 'listening') setState('idle', 'Ask SAGE anything');
      }
    });
    if (ok && V.listening()) { mic.setAttribute('aria-pressed', 'true'); setState('listening', 'Listening in ' + V.langLabel() + '...'); }
  });
  $('hushBtn').addEventListener('click', function () { V.stopSpeaking(); $('hushBtn').hidden = true; });

  /* ----------------------------------------------------------------- start */
  if (S.auth.get()) {
    S.api('GET', '/identity/me').then(function () { return enter(); }, function () { /* 401 emits signedout; network error shows the gate */ bootGate(); });
    $('gate').hidden = true;
  } else bootGate();
})();
