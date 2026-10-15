/* SAGE web app. Everything on this page comes from the real SAGE server (see sage-core.js).
   There are no scripted replies and no simulated sign-in: when the server cannot do something,
   this page says so. */
(function () {
  'use strict';

  var S = window.SAGE;
  var esc = S.esc, fmt = S.fmt, md = S.md, toast = S.toast;
  var $ = function (id) { return document.getElementById(id); };

  var signin = $('signin'), onboard = $('onboard'), shell = $('shell');
  var feed = $('feed'), inner = $('feedInner'), input = $('input'), sendBtn = $('sendBtn');
  var pane = $('pane'), paneBody = $('paneBody');

  var state = {
    profile: null, ownerMode: false, devMode: false,
    sessionId: null, projectId: null, projectName: '',
    busy: false, handle: null, taskId: null,
    pane: null, paneTimer: null, speak: false,
    lastText: ''
  };

  var ICONS = {
    research: '<circle cx="11" cy="11" r="6"/><path d="M16 16l4 4"/>',
    tasks: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 12l3 3 5-6"/>',
    projects: '<path d="M3 7h6l2 2h10v10H3z"/>',
    memory: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
    evolution: '<path d="M12 3l7 9-7 9-7-9z"/>',
    wallet: '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>',
    market: '<path d="M4 9l2-5h12l2 5v2H4z"/><path d="M5 11v9h14v-9"/>',
    learning: '<path d="M4 5h7v14H4zM13 5h7v14h-7z"/>',
    settings: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3"/>'
  };
  var FEATURES = [
    { id: 'research', label: 'Research', keys: ['research'] },
    { id: 'tasks', label: 'Tasks', keys: ['tasks', 'task list', 'work queue'] },
    { id: 'projects', label: 'Projects', keys: ['projects', 'project'] },
    { id: 'memory', label: 'Memory', keys: ['memory', 'memories'] },
    { id: 'evolution', label: 'Evolution', keys: ['evolution', 'rank', 'tier'] },
    { id: 'wallet', label: 'Spark wallet', keys: ['spark wallet', 'wallet', 'spark', 'balance'] },
    { id: 'market', label: 'Marketplace and jobs', keys: ['marketplace', 'market', 'jobs'] },
    { id: 'learning', label: 'Learning', keys: ['learning', 'lessons', 'courses'] },
    { id: 'settings', label: 'Settings', keys: ['settings', 'preferences'] }
  ];
  function featureById(id) { return FEATURES.filter(function (f) { return f.id === id; })[0]; }

  /* ---------------------------------------------------------------- boot */
  function show(which) {
    signin.hidden = which !== 'signin';
    onboard.hidden = which !== 'onboard';
    shell.hidden = which !== 'app';
  }
  function setSigninMsg(text) {
    var m = $('signinMsg');
    m.textContent = text || '';
    m.hidden = !text;
  }
  function setStatus(text, ok) {
    var s = $('serverStatus');
    s.textContent = text;
    s.className = 'server-status ' + (ok === true ? 'ok' : ok === false ? 'bad' : '');
  }

  function bootSignin(reason) {
    show('signin');
    $('retryBtn').hidden = true;
    $('devBtn').hidden = true;
    $('googleSlot').innerHTML = '';
    setSigninMsg(reason === 'expired' ? 'Your sign-in ended. Please sign in again.' : '');
    setStatus('Connecting to the SAGE server...');
    S.api('GET', '/identity/config', null, { noAuth: true, timeout: 70000 }).then(function (cfg) {
      state.devMode = !!cfg.developer_mode;
      setStatus('Connected to the SAGE server.', true);
      if (cfg.google_client_id) {
        S.renderGoogleButton($('googleSlot'), cfg.google_client_id, onGoogleCredential).catch(function () {
          setSigninMsg('Google sign-in could not load. A browser extension or network filter may be blocking accounts.google.com.');
          $('retryBtn').hidden = false;
        });
      } else if (!cfg.developer_mode) {
        setSigninMsg('Google sign-in is not set up on the SAGE server yet. The server owner needs to set GOOGLE_CLIENT_ID.');
      }
      if (cfg.developer_mode) {
        $('devBtn').hidden = false;
        if (!cfg.google_client_id) setStatus('Connected. This server is running in developer mode on your own computer.', true);
      }
    }, function (err) {
      setStatus(err.message, false);
      $('retryBtn').hidden = false;
    });
  }
  $('retryBtn').addEventListener('click', function () { bootSignin(); });

  function afterLogin(data) {
    return loadMe().then(function () {
      var needs = data && data.onboarding_required !== undefined ? data.onboarding_required : !(state.profile && state.profile.onboarding_completed);
      if (needs) return startOnboarding();
      enterApp();
    });
  }
  function onGoogleCredential(credential) {
    setSigninMsg('');
    setStatus('Signing you in...');
    S.loginWithGoogleCredential(credential).then(afterLogin).catch(function (err) {
      setStatus('Connected to the SAGE server.', true);
      if (err.status === 403) setSigninMsg('This SAGE server is private and this Google account is not its owner.');
      else setSigninMsg(err.message);
    });
  }
  $('devBtn').addEventListener('click', function () {
    setSigninMsg('');
    S.loginDeveloper('web-owner').then(afterLogin).catch(function (err) {
      setSigninMsg(err.status === 403 || err.status === 404 ? 'Developer sign-in only works when this page and the server are on the same computer.' : err.message);
    });
  });

  function loadMe() {
    return S.api('GET', '/identity/me').then(function (r) {
      state.profile = r.profile;
      state.ownerMode = !!r.owner_mode;
      state.devMode = !!r.developer_mode;
      return r;
    });
  }

  S.on('signedout', function (info) {
    if (state.handle) { state.handle.cancel(); }
    stopPaneTimer();
    state.sessionId = null;
    bootSignin(info && info.reason);
  });

  function init() {
    if (!S.base) {
      show('signin');
      setStatus('The SAGE server address is not set. Add apiBase to site-config.js.', false);
      return;
    }
    if (S.auth.get()) {
      show('signin');
      setStatus('Checking your sign-in...');
      loadMe().then(enterApp, function (err) {
        if (err.code === 'unauthorized') return; // signedout handler already showed sign-in
        bootSignin();
        setSigninMsg(err.message);
      });
    } else {
      bootSignin();
    }
  }

  /* ----------------------------------------------------------- onboarding */
  function startOnboarding() {
    show('onboard');
    var p = state.profile || {};
    $('obName').value = p.name || '';
    $('obAddress').value = p.address || '';
    $('obAge').value = p.age || '';
    $('obPhone').value = p.phone || '';
    $('obIntent').value = p.help_intent || '';
    $('obConsent').checked = !!p.memory_consent;
    $('obMsg').hidden = true;
    S.api('GET', '/identity/onboarding/options', null, { noAuth: true }).then(function (o) {
      var have = (p.capabilities || []);
      $('obCaps').innerHTML = (o.capabilities || []).map(function (c) {
        return '<label class="check"><input type="checkbox" value="' + esc(c.id) + '"' + (have.indexOf(c.id) !== -1 ? ' checked' : '') + '> <span>' + esc(c.label) + '</span></label>';
      }).join('');
    }, function (err) { $('obCaps').textContent = err.message; });
    $('obName').focus();
  }
  $('onboardForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var msg = $('obMsg');
    msg.hidden = true;
    var name = $('obName').value.trim(), address = $('obAddress').value.trim(), intent = $('obIntent').value.trim();
    var age = Number($('obAge').value);
    if (!name) return fail('Please enter your name.', 'obName');
    if (!address) return fail('Please enter where you live.', 'obAddress');
    if (!age || age < 1 || age > 120 || Math.floor(age) !== age) return fail('Please enter your age as a whole number.', 'obAge');
    if (!intent) return fail('Tell SAGE what you want help with.', 'obIntent');
    var caps = Array.prototype.map.call($('obCaps').querySelectorAll('input:checked'), function (i) { return i.value; });
    var phone = $('obPhone').value.trim();
    var body = { name: name, address: address, age: age, help_intent: intent, capabilities: caps, memory_consent: $('obConsent').checked };
    if (phone) body.phone = phone;
    $('obSave').disabled = true;
    S.api('POST', '/identity/onboarding', body).then(function (r) {
      state.profile = r.profile;
      toast('Saved. Welcome to SAGE.', 'ok');
      enterApp();
    }, function (err) { fail(err.message); }).then(function () { $('obSave').disabled = false; });
    function fail(text, id) { msg.textContent = text; msg.hidden = false; if (id) $(id).focus(); }
  });
  $('obSkip').addEventListener('click', function () { enterApp(); });

  /* ------------------------------------------------------------- app shell */
  function displayName() {
    var p = state.profile || {};
    return p.name || (p.email ? p.email.split('@')[0] : '') || 'there';
  }
  function enterApp() {
    show('app');
    var name = displayName();
    $('accName').textContent = name;
    $('accAvatar').textContent = name.trim().charAt(0).toUpperCase() || 'S';
    $('accMode').textContent = state.ownerMode ? (state.devMode ? 'Owner, developer mode' : 'Owner') : 'Member';
    renderNav();
    newChat();
    refreshBalance();
    refreshHistory();
    refreshBell();
    input.focus();
  }

  function renderNav() {
    $('nav').innerHTML = FEATURES.map(function (f) {
      return '<li><button type="button" data-feature="' + f.id + '"><svg viewBox="0 0 24 24" aria-hidden="true">' + ICONS[f.id] + '</svg><span>' + esc(f.label) + '</span></button></li>';
    }).join('');
    syncNav();
  }
  function syncNav() {
    Array.prototype.forEach.call($('nav').querySelectorAll('button'), function (b) {
      if (b.dataset.feature === state.pane) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
    });
  }
  function closeRail() { shell.classList.remove('rail-open'); $('scrim').hidden = true; }
  $('menuBtn').addEventListener('click', function () { shell.classList.add('rail-open'); $('scrim').hidden = false; });
  $('scrim').addEventListener('click', closeRail);
  $('nav').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-feature]');
    if (!b) return;
    openPane(b.dataset.feature);
    closeRail();
  });
  $('signOutBtn').addEventListener('click', function () { S.signOut(); });

  function refreshBalance() {
    S.api('GET', '/economy/me').then(function (r) {
      $('railBalance').textContent = fmt(r.spark.balance);
    }, function () { $('railBalance').textContent = 'unavailable'; });
  }

  function refreshHistory() {
    S.api('GET', '/sessions?limit=30').then(function (r) {
      var list = r.sessions || [];
      $('history').innerHTML = list.length ? list.map(function (s) {
        return '<li><button type="button" data-session="' + esc(s.id) + '" title="' + esc(s.title) + '"' + (s.id === state.sessionId ? ' aria-current="true"' : '') + '>' + esc(s.title) + '</button></li>';
      }).join('') : '<li class="rail-empty">No chats yet. Say hello.</li>';
    }, function (err) {
      $('history').innerHTML = '<li class="rail-empty">' + esc(err.message) + '</li>';
    });
  }
  $('history').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-session]');
    if (!b) return;
    loadSession(b.dataset.session, b.textContent);
    closeRail();
  });

  /* ------------------------------------------------------------------ chat */
  function scrollDown() { feed.scrollTop = feed.scrollHeight; }
  function clearFeed() { inner.innerHTML = ''; }

  function newChat() {
    if (state.busy && state.handle) { state.handle.cancel(); setBusy(false); }
    state.sessionId = null;
    $('chatTitle').textContent = 'New chat';
    clearFeed();
    var w = document.createElement('div');
    w.className = 'welcome';
    w.id = 'welcome';
    w.innerHTML = '<h2>Hello ' + esc(displayName()) + '. What are we working on?</h2>' +
      '<div class="suggest">' +
      '<button type="button" data-fill="Help me plan my week. Ask me what you need to know first."><b>Plan my week</b><small>SAGE asks what it needs</small></button>' +
      '<button type="button" data-fill="Research: "><b>Research something</b><small>Sources and evidence</small></button>' +
      '<button type="button" data-fill="What can you do for me right now, and what can you not do yet?"><b>What can you do?</b><small>An honest answer</small></button>' +
      '<button type="button" data-fill="Teach me one useful skill today."><b>Learn something</b><small>A short lesson</small></button>' +
      '</div>';
    inner.appendChild(w);
    Array.prototype.forEach.call($('history').querySelectorAll('button'), function (b) { b.removeAttribute('aria-current'); });
    input.value = '';
    autosize();
  }
  $('newChat').addEventListener('click', function () { newChat(); closeRail(); input.focus(); });

  inner.addEventListener('click', function (e) {
    var f = e.target.closest('button[data-fill]');
    if (f) { input.value = f.dataset.fill; autosize(); input.focus(); sendBtn.disabled = !input.value.trim(); return; }
    var r = e.target.closest('button[data-retry]');
    if (r) { var t = r.dataset.retry; r.closest('.msg').remove(); send(t, true); return; }
    var o = e.target.closest('button[data-open]');
    if (o) openPane(o.dataset.open);
  });

  function addMsg(who, html, cls) {
    var w = $('welcome'); if (w) w.remove();
    var el = document.createElement('div');
    el.className = 'msg ' + who + (cls ? ' ' + cls : '');
    el.innerHTML = '<span class="who" aria-hidden="true">' + (who === 'sage' ? '' : 'You') + '</span><div class="body"><div class="text"></div></div>';
    el.querySelector('.text').innerHTML = html;
    inner.appendChild(el);
    scrollDown();
    return el;
  }
  function plain(text) { return esc(text).replace(/\n/g, '<br>'); }

  function loadSession(id, title) {
    if (state.busy) return toast('Wait for SAGE to finish, or stop it first.', 'err');
    clearFeed();
    var el = addMsg('sage', '<span class="muted">Loading this chat...</span>');
    S.api('GET', '/session/' + encodeURIComponent(id) + '/messages?limit=100').then(function (r) {
      clearFeed();
      state.sessionId = id;
      $('chatTitle').textContent = title || 'Chat';
      (r.messages || []).forEach(function (m) {
        if (m.role === 'user') addMsg('you', plain(m.content));
        else if (m.role === 'assistant') addMsg('sage', md(m.content));
      });
      refreshHistory();
      scrollDown();
    }, function (err) {
      el.remove();
      toast(err.message, 'err');
      newChat();
    });
  }

  function setBusy(b) {
    state.busy = b;
    sendBtn.classList.toggle('stop', b);
    sendBtn.setAttribute('aria-label', b ? 'Stop' : 'Send');
    sendBtn.disabled = b ? false : !input.value.trim();
    sendBtn.innerHTML = b
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 19V5M6 11l6-6 6 6"/></svg>';
  }

  function statusLabel(task) {
    if (!task) return 'Sending to SAGE...';
    var retries = task.retries || 0;
    if (task.status === 'pending') {
      return retries > 0 ? 'Retrying (' + retries + ' of ' + (task.max_retries || 3) + ')...' : 'Waiting for a SAGE worker...';
    }
    if (task.status === 'running') return 'SAGE is working' + (task.progress ? ' (' + Math.round(task.progress * (task.progress <= 1 ? 100 : 1)) + '%)' : '') + '...';
    return 'Working...';
  }

  function intentPane(text) {
    var t = text.toLowerCase().replace(/[.!?]+$/, '').trim();
    var m = /^(open|show|go to|take me to|show me)\s+(my\s+|the\s+)?(.+)$/.exec(t);
    if (!m) return null;
    var target = m[3].trim();
    for (var i = 0; i < FEATURES.length; i++) {
      for (var k = 0; k < FEATURES[i].keys.length; k++) { if (target === FEATURES[i].keys[k]) return FEATURES[i].id; }
    }
    return null;
  }

  function send(text, isRetry) {
    text = (text || '').trim();
    if (!text) return;
    if (state.busy) return;
    var nav = intentPane(text);
    if (nav) {
      input.value = ''; autosize(); sendBtn.disabled = true;
      addMsg('you', plain(text));
      addMsg('sage', 'Opening ' + esc(featureById(nav).label) + ' on the right.');
      openPane(nav);
      return;
    }
    if (text.length > 8000) return toast('That message is too long. Keep it under 8,000 characters.', 'err');
    state.lastText = text;
    if (!isRetry) addMsg('you', plain(text));
    if ($('chatTitle').textContent === 'New chat') $('chatTitle').textContent = text.length > 38 ? text.slice(0, 38) + '...' : text;
    input.value = '';
    autosize();
    setBusy(true);
    var holder = addMsg('sage', '<span class="typing" aria-hidden="true"><i></i><i></i><i></i></span> <span class="status">Sending to SAGE...</span>');
    var statusEl = function () { return holder.querySelector('.status'); };
    var handle = S.sendCommand(text, {
      sessionId: state.sessionId,
      projectId: state.projectId,
      onQueued: function (q) { state.sessionId = q.sessionId; state.taskId = q.task && q.task.id; },
      onStatus: function (task) { var s = statusEl(); if (s) s.textContent = statusLabel(task); }
    });
    state.handle = handle;
    handle.promise.then(function (r) {
      holder.querySelector('.text').innerHTML = md(r.text);
      setBusy(false);
      scrollDown();
      if (state.speak) speak(r.text);
      refreshHistory();
      refreshBalance();
      refreshBell();
    }, function (err) {
      var stopped = err && err.message === 'Stopped.';
      holder.classList.add(stopped ? 'stopped' : 'error');
      holder.querySelector('.text').innerHTML = '<p>' + esc(err.message || 'Something went wrong.') + '</p>' +
        (stopped ? '' : '<button type="button" class="btn small" data-retry="' + esc(text) + '">Try again</button>');
      setBusy(false);
      scrollDown();
    });
  }

  sendBtn.addEventListener('click', function (e) {
    if (state.busy) {
      e.preventDefault();
      if (state.handle) state.handle.cancel();
      if (state.taskId) S.api('POST', '/tasks/' + encodeURIComponent(state.taskId) + '/cancel').catch(function () { /* already finished */ });
    }
  });
  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 180) + 'px'; }
  input.addEventListener('input', function () { autosize(); if (!state.busy) sendBtn.disabled = !input.value.trim(); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!state.busy) send(input.value); }
  });
  $('composer').addEventListener('submit', function (e) { e.preventDefault(); if (!state.busy) send(input.value); });

  /* ------------------------------------------------------------------ voice */
  var recog = null, mic = $('micBtn');
  function note(t) {
    var el = document.createElement('p');
    el.className = 'fine sys';
    el.textContent = t;
    inner.appendChild(el);
    scrollDown();
  }
  mic.addEventListener('click', function () {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return note('Voice input is not available in this browser. Try Chrome or Edge, or type your message.');
    if (recog) { recog.stop(); return; }
    try {
      recog = new SR();
      recog.lang = 'en-US';
      recog.interimResults = true;
      recog.continuous = false;
      var finalText = '';
      recog.onresult = function (e) {
        var interim = '';
        for (var i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) finalText += e.results[i][0].transcript; else interim += e.results[i][0].transcript;
        }
        input.value = (finalText + interim).trim(); autosize(); sendBtn.disabled = !input.value.trim();
      };
      recog.onerror = function (e) {
        note(e.error === 'not-allowed' ? 'Microphone access was blocked. Allow the microphone for this site, or type your message.' : 'SAGE could not hear you. Try again or type your message.');
      };
      recog.onend = function () {
        mic.setAttribute('aria-pressed', 'false'); mic.classList.remove('live');
        recog = null;
        if (finalText.trim()) send(input.value);
      };
      recog.start();
      mic.setAttribute('aria-pressed', 'true'); mic.classList.add('live');
    } catch (err) {
      recog = null;
      note('Voice input could not start. Type your message instead.');
    }
  });
  var speakBtn = $('speakBtn');
  speakBtn.addEventListener('click', function () {
    if (!('speechSynthesis' in window)) return toast('This browser cannot read aloud.', 'err');
    state.speak = !state.speak;
    speakBtn.setAttribute('aria-pressed', String(state.speak));
    if (!state.speak) window.speechSynthesis.cancel();
    toast(state.speak ? 'SAGE will read replies aloud.' : 'Reading aloud is off.', 'ok');
  });
  function speak(text) {
    try {
      var plainText = String(text).replace(/```[\s\S]*?```/g, ' code block ').replace(/[*_`#>]/g, '').slice(0, 1500);
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(new SpeechSynthesisUtterance(plainText));
    } catch (e) { /* speech is optional */ }
  }

  /* ----------------------------------------------------- notifications bell */
  function refreshBell() {
    S.api('GET', '/notifications').then(function (r) {
      var unread = (r.notifications || []).filter(function (n) { return !n.read; }).length;
      var b = $('bellBadge');
      b.textContent = unread > 9 ? '9+' : String(unread);
      b.hidden = unread === 0;
    }, function () { /* the bell is optional */ });
  }
  $('bellBtn').addEventListener('click', function () { openPane('notifications'); });

  /* ------------------------------------------------------------ active project */
  function setProject(id, name) {
    state.projectId = id || null;
    state.projectName = name || '';
    var chip = $('projectChip');
    chip.hidden = !id;
    chip.textContent = id ? 'Project: ' + name + '  ×' : '';
  }
  $('projectChip').addEventListener('click', function () { setProject(null); toast('No project selected.', 'ok'); });

  /* ================================================================= panes */
  function stopPaneTimer() { if (state.paneTimer) { clearInterval(state.paneTimer); state.paneTimer = null; } }
  function closePane() {
    state.pane = null;
    stopPaneTimer();
    pane.hidden = true;
    shell.classList.remove('with-pane');
    syncNav();
  }
  $('paneClose').addEventListener('click', closePane);

  function openPane(id) {
    var def = PANES[id];
    if (!def) return;
    stopPaneTimer();
    state.pane = id;
    $('paneTitle').textContent = def.title;
    pane.hidden = false;
    shell.classList.add('with-pane');
    syncNav();
    renderPane(id);
  }
  function renderPane(id) {
    var def = PANES[id];
    paneBody.innerHTML = '<p class="muted pane-loading">Loading...</p>';
    def.render(paneBody).then(null, function (err) {
      paneBody.innerHTML = '<div class="card"><h3>Could not load this</h3><p class="muted">' + esc(err.message || 'Unknown error') + '</p><button type="button" class="btn small" data-reload="1">Try again</button></div>';
    });
  }
  paneBody.addEventListener('click', function (e) {
    if (e.target.closest('[data-reload]')) { renderPane(state.pane); return; }
  });
  function paneIs(id) { return state.pane === id; }
  function tag(status) {
    var cls = { completed: 'ok', running: 'blue', pending: '', paused: '', failed: 'fail', cancelled: 'fail', open: 'ok', closed: '' }[status] || '';
    return '<span class="tag ' + cls + '">' + esc(status) + '</span>';
  }
  function fieldRow(id, label, extra) {
    return '<div class="field"><label for="' + id + '">' + esc(label) + '</label>' + extra + '</div>';
  }
  function npr(n) { return 'NPR ' + fmt(Math.round(Number(n) || 0)); }

  var PANES = {};

  /* ---- tasks */
  PANES.tasks = {
    title: 'Tasks',
    render: function (el) {
      function draw(first) {
        return S.api('GET', '/tasks').then(function (r) {
          if (!paneIs('tasks')) return;
          var list = (r.tasks || []).slice().sort(function (a, b) { return String(b.created_at).localeCompare(String(a.created_at)); });
          var active = list.some(function (t) { return t.status === 'pending' || t.status === 'running'; });
          var open = {};
          Array.prototype.forEach.call(el.querySelectorAll('details[open]'), function (d) { open[d.dataset.id] = true; });
          el.innerHTML = list.length ? '<ul class="list tasklist">' + list.map(function (t) {
            var body = t.status === 'completed' ? '<div class="md">' + md(S.resultText(t)) + '</div>' :
              t.error ? '<p class="err-text">' + esc(t.error) + '</p>' : '<p class="muted">' + esc(t.description || '') + '</p>';
            var cancel = (t.status === 'pending' || t.status === 'running') ? '<button type="button" class="btn small" data-cancel="' + esc(t.id) + '">Cancel</button>' : '';
            return '<li><details data-id="' + esc(t.id) + '"' + (open[t.id] ? ' open' : '') + '><summary><span>' + esc(t.title) + '<small>' + esc(t.agent) + ' · ' + esc(S.relTime(t.created_at)) + '</small></span>' + tag(t.status) + '</summary>' + body + cancel + '</details></li>';
          }).join('') + '</ul>' : '<div class="card"><h3>No tasks yet</h3><p class="muted">Everything you ask SAGE in chat becomes a task. They appear here with their results.</p></div>';
          if (active && first) state.paneTimer = setInterval(function () { if (paneIs('tasks')) draw(false); else stopPaneTimer(); }, 4000);
          if (!active) stopPaneTimer();
        });
      }
      el.onclick = function (e) {
        var c = e.target.closest('button[data-cancel]');
        if (!c) return;
        c.disabled = true;
        S.api('POST', '/tasks/' + encodeURIComponent(c.dataset.cancel) + '/cancel').then(function () { toast('Cancelled.', 'ok'); draw(false); }, function (err) { toast(err.message, 'err'); c.disabled = false; });
      };
      return draw(true);
    }
  };

  /* ---- research */
  PANES.research = {
    title: 'Research',
    render: function (el) {
      return S.api('GET', '/tasks').then(function (r) {
        var list = (r.tasks || []).filter(function (t) { return t.agent === 'research'; }).sort(function (a, b) { return String(b.created_at).localeCompare(String(a.created_at)); });
        el.innerHTML = '<form class="card" id="rForm"><label class="fine" for="rq">What should SAGE research?</label>' +
          '<div class="field"><input id="rq" type="text" maxlength="500" autocomplete="off"></div>' +
          '<button type="submit" class="btn primary small">Start research</button>' +
          '<p class="fine">SAGE searches the web, cross-checks sources and gives you evidence. The answer arrives in chat and is kept under Tasks.</p></form>' +
          (list.length ? '<h3 class="sub">Recent research</h3><ul class="list">' + list.slice(0, 12).map(function (t) {
            return '<li><details><summary><span>' + esc(t.title) + '<small>' + esc(S.relTime(t.created_at)) + '</small></span>' + tag(t.status) + '</summary>' +
              (t.status === 'completed' ? '<div class="md">' + md(S.resultText(t)) + '</div>' : t.error ? '<p class="err-text">' + esc(t.error) + '</p>' : '<p class="muted">Still in progress.</p>') + '</details></li>';
          }).join('') + '</ul>' : '<p class="muted">No research yet.</p>');
        $('rForm').addEventListener('submit', function (e) {
          e.preventDefault();
          var q = $('rq').value.trim();
          if (q.length < 3) return toast('Type what you want researched.', 'err');
          closePane();
          send('Research: ' + q);
        });
      });
    }
  };

  /* ---- projects */
  PANES.projects = {
    title: 'Projects',
    render: function (el) {
      return S.api('GET', '/workflow/workspaces').then(function (r) {
        var spaces = r.workspaces || [];
        return Promise.all(spaces.map(function (w) {
          return S.api('GET', '/workflow/workspaces/' + encodeURIComponent(w.id) + '/projects').then(function (p) { return { w: w, projects: p.projects || [] }; });
        }));
      }).then(function (groups) {
        var html = '<form class="card" id="pForm"><h3>New project</h3>' +
          '<div class="field"><label for="pn">Project name</label><input id="pn" type="text" maxlength="200" autocomplete="off"></div>' +
          '<div class="field"><label for="pd">What is it? (optional)</label><input id="pd" type="text" maxlength="500" autocomplete="off"></div>' +
          '<button type="submit" class="btn primary small">Create project</button></form>';
        var any = false;
        groups.forEach(function (g) {
          g.projects.forEach(function (p) {
            any = true;
            html += '<div class="card"><div class="row-between"><h3>' + esc(p.name) + '</h3>' + (state.projectId === p.id ? '<span class="tag ok">Active</span>' : '<button type="button" class="btn small" data-use="' + esc(p.id) + '" data-name="' + esc(p.name) + '">Use in chat</button>') + '</div>' +
              (p.description ? '<p class="muted">' + esc(p.description) + '</p>' : '') +
              '<button type="button" class="linkbtn" data-assets="' + esc(p.id) + '">Saved results</button><div class="assets" data-for="' + esc(p.id) + '"></div></div>';
          });
        });
        if (!any) html += '<p class="muted">No projects yet. Create one, then choose "Use in chat" so SAGE saves its results there.</p>';
        el.innerHTML = html;
        $('pForm').addEventListener('submit', function (e) {
          e.preventDefault();
          var name = $('pn').value.trim();
          if (!name) return toast('Give the project a name.', 'err');
          var space = groups[0] ? Promise.resolve(groups[0].w) : S.api('POST', '/workflow/workspaces', { name: 'Personal', slug: 'personal-' + Math.random().toString(36).slice(2, 7) }).then(function (r) { return r.workspace; });
          space.then(function (w) {
            return S.api('POST', '/workflow/workspaces/' + encodeURIComponent(w.id) + '/projects', { name: name, description: $('pd').value.trim() || null });
          }).then(function () { toast('Project created.', 'ok'); renderPane('projects'); }, function (err) { toast(err.message, 'err'); });
        });
        el.onclick = function (e) {
          var u = e.target.closest('button[data-use]');
          if (u) { setProject(u.dataset.use, u.dataset.name); toast('SAGE will save results in ' + u.dataset.name + '.', 'ok'); renderPane('projects'); return; }
          var a = e.target.closest('button[data-assets]');
          if (a) {
            var box = el.querySelector('.assets[data-for="' + a.dataset.assets + '"]');
            box.textContent = 'Loading...';
            S.api('GET', '/workflow/projects/' + encodeURIComponent(a.dataset.assets) + '/assets').then(function (r) {
              var items = r.assets || [];
              box.innerHTML = items.length ? '<ul class="list">' + items.map(function (x) { return '<li><span>' + esc(x.name) + '<small>' + esc(x.asset_type) + ' · ' + esc(S.relTime(x.created_at)) + '</small></span><span class="tag">' + esc(x.status) + '</span></li>'; }).join('') + '</ul>' : '<p class="muted">Nothing saved yet.</p>';
            }, function (err) { box.textContent = err.message; });
          }
          if (e.target.closest('[data-reload]')) renderPane('projects');
        };
      });
    }
  };

  /* ---- memory */
  PANES.memory = {
    title: 'Memory',
    render: function (el) {
      return Promise.all([S.api('GET', '/identity/memory'), loadMe()]).then(function (res) {
        var mems = res[0].memories || [];
        var consent = !!(state.profile && state.profile.memory_consent);
        var pending = mems.filter(function (m) { return m.source === 'auto_learning' && !m.confirmed; });
        var kept = mems.filter(function (m) { return !(m.source === 'auto_learning' && !m.confirmed); });
        var html = '<div class="card"><label class="switch"><span>Let SAGE suggest memories<small class="fine" style="display:block">SAGE only keeps something after you approve it.</small></span><input type="checkbox" id="consentSw"' + (consent ? ' checked' : '') + ' aria-label="Let SAGE suggest memories"></label></div>';
        if (pending.length) {
          html += '<h3 class="sub">Waiting for your review</h3><ul class="list">' + pending.map(function (m) {
            return '<li><span>' + esc(m.content) + '<small>' + esc(m.memory_type) + '</small></span><span class="row-actions"><button type="button" class="btn small primary" data-keep="' + esc(m.id) + '">Keep</button><button type="button" class="btn small" data-del="' + esc(m.id) + '">Reject</button></span></li>';
          }).join('') + '</ul>';
        }
        html += '<h3 class="sub">What SAGE remembers</h3>' + (kept.length ? '<ul class="list">' + kept.map(function (m) {
          return '<li><span>' + esc(m.content) + '<small>' + esc(m.memory_type) + ' · ' + esc(S.relTime(m.created_at)) + '</small></span><button type="button" class="btn small" data-del="' + esc(m.id) + '" aria-label="Forget this">Forget</button></li>';
        }).join('') + '</ul>' : '<p class="muted">Nothing yet. Add something below, or tell SAGE about yourself.</p>');
        html += '<form class="card" id="mForm"><h3>Add a memory</h3><div class="field"><label for="mt">Type</label><select id="mt"><option value="fact">Fact about me</option><option value="preference">Preference</option><option value="goal">Goal</option><option value="interest">Interest</option><option value="skill">Skill</option><option value="experience">Experience</option></select></div>' +
          '<div class="field"><label for="mc">What should SAGE remember?</label><textarea id="mc" rows="2" maxlength="5000"></textarea></div><button type="submit" class="btn primary small">Save memory</button></form>';
        el.innerHTML = html;
        $('consentSw').addEventListener('change', function (e) {
          S.api('PATCH', '/identity/me', { memory_consent: e.target.checked }).then(function (r) { state.profile = r.profile; toast(e.target.checked ? 'SAGE may now suggest memories.' : 'SAGE will not suggest memories.', 'ok'); }, function (err) { toast(err.message, 'err'); e.target.checked = !e.target.checked; });
        });
        $('mForm').addEventListener('submit', function (e) {
          e.preventDefault();
          var c = $('mc').value.trim();
          if (!c) return toast('Write what SAGE should remember.', 'err');
          S.api('POST', '/identity/memory', { memory_type: $('mt').value, content: c, source: 'user', confirmed: true }).then(function () { toast('Saved.', 'ok'); renderPane('memory'); }, function (err) { toast(err.message, 'err'); });
        });
        el.onclick = function (e) {
          var k = e.target.closest('button[data-keep]'), d = e.target.closest('button[data-del]');
          if (k) S.api('PATCH', '/identity/memory/' + encodeURIComponent(k.dataset.keep), { confirmed: true }).then(function () { toast('Kept.', 'ok'); renderPane('memory'); }, function (err) { toast(err.message, 'err'); });
          if (d) S.api('DELETE', '/identity/memory/' + encodeURIComponent(d.dataset.del)).then(function () { toast('Removed.', 'ok'); renderPane('memory'); }, function (err) { toast(err.message, 'err'); });
          if (e.target.closest('[data-reload]')) renderPane('memory');
        };
      });
    }
  };

  /* ---- evolution */
  PANES.evolution = {
    title: 'Evolution',
    render: function (el) {
      return Promise.all([S.api('GET', '/economy/me'), S.api('GET', '/economy/evolution/tiers')]).then(function (res) {
        var evo = res[0].evolution, tiers = res[1].tiers || [];
        var ratio = Math.max(0, Math.min(1, (evo.progress && evo.progress.ratio) || 0));
        var next = evo.progress && evo.progress.next_tier;
        el.innerHTML = '<div class="card"><div class="row-between"><h3>' + esc(evo.tier) + '</h3><span class="tag blue">' + esc(String(evo.stage).toLowerCase()) + '</span></div>' +
          '<div class="bar" role="progressbar" aria-valuenow="' + Math.round(ratio * 100) + '" aria-valuemin="0" aria-valuemax="100" aria-label="Progress to the next Evolution"><i style="width:' + Math.round(ratio * 100) + '%"></i></div>' +
          '<p class="muted">' + (next ? Math.round(ratio * 100) + '% of the way to ' + esc(next) + '. ' : 'This is the final Evolution. ') + 'Lifetime achievement: <b class="num">' + fmt(evo.lifetime_achievement) + '</b>. Spending Spark never lowers it.</p></div>' +
          '<div class="card"><h3>The 13 Evolutions</h3><ol class="tiers">' + tiers.map(function (t) {
            var cls = t.tier === evo.tier ? ' class="on"' : '';
            return '<li' + cls + '><span>' + esc(t.tier) + '</span><span class="num">' + fmt(t.threshold) + '</span></li>';
          }).join('') + '</ol><p class="fine">Numbers are the lifetime achievement needed to reach each rank.</p></div>' +
          '<div class="card"><h3>Two paths</h3><p class="muted"><b>Skill</b> changes how SAGE looks and who it is. <b>Money</b> changes what it is allowed to do.</p></div>';
      });
    }
  };

  /* ---- wallet */
  PANES.wallet = {
    title: 'Spark wallet',
    render: function (el) {
      return Promise.all([S.api('GET', '/economy/me'), S.api('GET', '/economy/spend-limit'), S.api('GET', '/economy/costs'), S.api('GET', '/economy/currency')]).then(function (res) {
        var sp = res[0].spark, ledger = res[0].ledger || [], lim = res[1].spend_limit, costs = res[2].costs || [], cur = res[3].currency;
        el.innerHTML = '<div class="card"><span class="fine">Spark balance</span><div class="big-gold num">' + fmt(sp.balance) + '</div>' +
          '<p class="muted">= NPR ' + fmt(sp.npr_value) + ' (' + esc(cur.rule) + ')</p>' +
          '<div class="row-between"><span class="fine">Earned ' + fmt(sp.lifetime_earned) + '</span><span class="fine">Spent ' + fmt(sp.lifetime_spent) + '</span></div></div>' +
          '<div class="card"><h3>Spend limit</h3><p class="muted">' + esc(lim.note || '') + '</p>' +
          '<ul class="list"><li><span>Money level</span><b>' + esc(lim.level || 'None yet') + '</b></li><li><span>Locked as savings</span><b class="num">' + fmt(lim.savings_locked) + '</b></li><li><span>SAGE may propose up to</span><b class="num">' + fmt(lim.per_spend_limit) + ' Spark</b></li></ul>' +
          '<p class="fine">You approve every spend. These limits are a draft until you confirm them.</p></div>' +
          '<div class="card"><h3>Premium work</h3><ul class="list">' + costs.map(function (c) { return '<li><span>' + esc(c.name) + '<small>' + esc(c.description) + '</small></span><b class="num">' + fmt(c.spark_cost) + ' Spark</b></li>'; }).join('') + '</ul></div>' +
          '<div class="card"><h3>Recent activity</h3>' + (ledger.length ? '<ul class="list">' + ledger.slice(0, 15).map(function (l) {
            var amt = Number(l.amount != null ? l.amount : l.delta || 0);
            return '<li><span>' + esc(l.reason || l.entry_type || l.type || 'Entry') + '<small>' + esc(S.relTime(l.created_at)) + '</small></span><b class="num">' + (amt > 0 ? '+' : '') + fmt(amt) + '</b></li>';
          }).join('') + '</ul>' : '<p class="muted">No activity yet. Every account starts at 0 Spark.</p>') + '</div>' +
          '<div class="card"><span class="tag fail" style="width:max-content">' + (cur.payout_available ? 'Cash-out available' : 'Cash-out is not available yet') + '</span><p class="fine">' + esc(cur.payout_message || '') + '</p></div>';
      });
    }
  };

  /* ---- marketplace and jobs */
  PANES.market = {
    title: 'Marketplace and jobs',
    render: function (el) {
      var tab = 'listings';
      function draw() {
        var call = tab === 'listings' ? S.api('GET', '/marketplace/listings') : S.api('GET', '/jobs');
        return call.then(function (r) {
          var items = tab === 'listings' ? (r.listings || []) : (r.jobs || []);
          var html = '<div class="chips tabs" role="group" aria-label="Section"><button type="button" class="chip-link" data-tab="listings" aria-pressed="' + (tab === 'listings') + '">Marketplace</button><button type="button" class="chip-link" data-tab="jobs" aria-pressed="' + (tab === 'jobs') + '">Jobs</button></div>';
          if (tab === 'listings') {
            html += items.length ? '<ul class="list">' + items.map(function (l) {
              return '<li><details><summary><span>' + esc(l.title) + '<small>' + esc(l.location) + ' · ' + esc(l.category) + ' · ' + esc(l.item_condition) + '</small></span><b class="num">' + npr(l.price_npr) + '</b></summary><p class="muted">' + esc(l.description) + '</p><p class="fine">Seller: ' + esc(l.seller_name) + '</p>' +
                '<div class="field"><label for="inq-' + esc(l.id) + '">Message the seller</label><textarea id="inq-' + esc(l.id) + '" rows="2" maxlength="3000"></textarea></div><button type="button" class="btn small primary" data-inquire="' + esc(l.id) + '">Send message</button></details></li>';
            }).join('') + '</ul>' : '<p class="muted">No listings yet. Post the first one below.</p>';
            html += '<form class="card" id="listForm"><h3>Post a listing</h3>' +
              fieldRow('lt', 'Title', '<input id="lt" type="text" maxlength="160">') +
              fieldRow('lc', 'Category', '<select id="lc"><option value="vehicles">Vehicles</option><option value="electronics">Electronics</option><option value="property">Property</option><option value="services">Services</option><option value="courses">Courses</option><option value="home">Home</option><option value="other">Other</option></select>') +
              fieldRow('ld', 'Description', '<textarea id="ld" rows="3" maxlength="12000"></textarea>') +
              fieldRow('ll', 'Location', '<input id="ll" type="text" maxlength="160">') +
              fieldRow('lp', 'Price (NPR)', '<input id="lp" type="number" min="1" step="1" inputmode="numeric">') +
              fieldRow('lk', 'Condition', '<select id="lk"><option value="new">New</option><option value="used" selected>Used</option></select>') +
              '<button type="submit" class="btn primary small">Post listing</button></form>';
          } else {
            html += items.length ? '<ul class="list">' + items.map(function (j) {
              var pay = j.salary_min_npr || j.salary_max_npr ? npr(j.salary_min_npr) + (j.salary_max_npr ? ' to ' + npr(j.salary_max_npr) : '') : 'Pay not listed';
              return '<li><details><summary><span>' + esc(j.title) + '<small>' + esc(j.company) + ' · ' + esc(j.location) + ' · ' + esc(String(j.employment_type).replace('_', ' ')) + '</small></span><span class="tag">' + esc(j.status) + '</span></summary><p class="muted">' + esc(j.description) + '</p><p class="fine">' + esc(pay) + '</p>' +
                '<div class="field"><label for="app-' + esc(j.id) + '">Cover note</label><textarea id="app-' + esc(j.id) + '" rows="2" maxlength="5000"></textarea></div><button type="button" class="btn small primary" data-apply="' + esc(j.id) + '">Apply</button></details></li>';
            }).join('') + '</ul>' : '<p class="muted">No jobs yet. Post the first one below.</p>';
            html += '<form class="card" id="jobForm"><h3>Post a job</h3>' +
              fieldRow('jt', 'Job title', '<input id="jt" type="text" maxlength="160">') +
              fieldRow('jc', 'Company', '<input id="jc" type="text" maxlength="160">') +
              fieldRow('jl', 'Location', '<input id="jl" type="text" maxlength="160">') +
              fieldRow('jd', 'Description', '<textarea id="jd" rows="3" maxlength="12000"></textarea>') +
              fieldRow('jy', 'Type', '<select id="jy"><option value="full_time">Full time</option><option value="part_time">Part time</option><option value="contract">Contract</option><option value="internship">Internship</option></select>') +
              '<button type="submit" class="btn primary small">Post job</button></form>';
          }
          el.innerHTML = html;
        });
      }
      el.onclick = function (e) {
        var t = e.target.closest('button[data-tab]');
        if (t) { tab = t.dataset.tab; el.innerHTML = '<p class="muted">Loading...</p>'; draw().then(null, showErr); return; }
        var q = e.target.closest('button[data-inquire]');
        if (q) {
          var msg = $('inq-' + q.dataset.inquire).value.trim();
          if (!msg) return toast('Write a message first.', 'err');
          q.disabled = true;
          S.api('POST', '/marketplace/listings/' + encodeURIComponent(q.dataset.inquire) + '/inquiries', { message: msg }).then(function () { toast('Message sent to the seller.', 'ok'); $('inq-' + q.dataset.inquire).value = ''; }, function (err) { toast(err.message, 'err'); }).then(function () { q.disabled = false; });
        }
        var a = e.target.closest('button[data-apply]');
        if (a) {
          a.disabled = true;
          S.api('POST', '/jobs/' + encodeURIComponent(a.dataset.apply) + '/applications', { cover_note: $('app-' + a.dataset.apply).value.trim() }).then(function () { toast('Application sent.', 'ok'); }, function (err) { toast(err.message, 'err'); }).then(function () { a.disabled = false; });
        }
        if (e.target.closest('[data-reload]')) renderPane('market');
      };
      el.onsubmit = function (e) {
        e.preventDefault();
        if (e.target.id === 'listForm') {
          var price = Number($('lp').value);
          if (!$('lt').value.trim() || !$('ld').value.trim() || !$('ll').value.trim()) return toast('Fill in the title, description and location.', 'err');
          if (!(price > 0)) return toast('Enter a price above 0.', 'err');
          S.api('POST', '/marketplace/listings', { title: $('lt').value.trim(), category: $('lc').value, description: $('ld').value.trim(), location: $('ll').value.trim(), price_npr: price, item_condition: $('lk').value })
            .then(function () { toast('Listing posted.', 'ok'); draw(); }, function (err) { toast(err.message, 'err'); });
        } else if (e.target.id === 'jobForm') {
          if (!$('jt').value.trim() || !$('jc').value.trim() || !$('jl').value.trim() || !$('jd').value.trim()) return toast('Fill in every field.', 'err');
          S.api('POST', '/jobs', { title: $('jt').value.trim(), company: $('jc').value.trim(), location: $('jl').value.trim(), description: $('jd').value.trim(), employment_type: $('jy').value })
            .then(function () { toast('Job posted.', 'ok'); draw(); }, function (err) { toast(err.message, 'err'); });
        }
      };
      function showErr(err) { el.innerHTML = '<div class="card"><h3>Could not load this</h3><p class="muted">' + esc(err.message) + '</p><button type="button" class="btn small" data-reload="1">Try again</button></div>'; }
      return draw();
    }
  };

  /* ---- learning */
  PANES.learning = {
    title: 'Learning',
    render: function (el) {
      return S.api('GET', '/learning/paths').then(function (r) {
        var paths = r.paths || [];
        el.innerHTML = paths.length ? paths.map(function (p) {
          var done = p.lessons.filter(function (l) { return l.is_completed; }).length;
          return '<div class="card"><div class="row-between"><h3>' + esc(p.title) + '</h3><span class="tag ' + (done === p.lessons.length ? 'ok' : 'blue') + '">' + done + ' of ' + p.lessons.length + '</span></div><p class="muted">' + esc(p.subtitle || '') + ' · ' + esc(p.level) + ' · ' + esc(p.estimated_minutes) + ' min</p>' +
            '<ul class="list">' + p.lessons.map(function (l) {
              return '<li><details><summary><span>' + esc(l.title) + '<small>' + esc(l.minutes) + ' min</small></span>' + (l.is_completed ? '<span class="tag ok">Done</span>' : '<span class="tag">Open</span>') + '</summary><p class="muted"><b>Goal:</b> ' + esc(l.objective) + '</p><p>' + esc(l.content) + '</p><p class="muted"><b>Try this:</b> ' + esc(l.exercise) + '</p>' +
                (l.is_completed ? '' : '<button type="button" class="btn small primary" data-complete="' + esc(l.id) + '">Mark complete</button>') + '</details></li>';
            }).join('') + '</ul></div>';
        }).join('') : '<p class="muted">No lessons available.</p>';
        el.onclick = function (e) {
          var c = e.target.closest('button[data-complete]');
          if (c) {
            c.disabled = true;
            S.api('POST', '/learning/lessons/' + encodeURIComponent(c.dataset.complete) + '/complete').then(function () { toast('Lesson complete.', 'ok'); renderPane('learning'); }, function (err) { toast(err.message, 'err'); c.disabled = false; });
          }
          if (e.target.closest('[data-reload]')) renderPane('learning');
        };
      });
    }
  };

  /* ---- notifications */
  PANES.notifications = {
    title: 'Notifications',
    render: function (el) {
      return S.api('GET', '/notifications').then(function (r) {
        var list = r.notifications || [];
        el.innerHTML = list.length ? '<div class="row-between"><span class="fine">' + list.filter(function (n) { return !n.read; }).length + ' unread</span><button type="button" class="btn small" data-readall="1">Mark all read</button></div><ul class="list">' + list.map(function (n) {
          return '<li><span>' + esc(n.title) + '<small>' + esc(n.body || '') + ' · ' + esc(S.relTime(n.created_at)) + '</small></span>' + (n.read ? '<span class="tag">Read</span>' : '<button type="button" class="btn small" data-read="' + esc(n.id) + '">Mark read</button>') + '</li>';
        }).join('') + '</ul>' : '<div class="card"><h3>Nothing new</h3><p class="muted">SAGE tells you here when background work finishes.</p></div>';
        el.onclick = function (e) {
          var one = e.target.closest('button[data-read]'), all = e.target.closest('button[data-readall]');
          if (one) S.api('POST', '/notifications/' + encodeURIComponent(one.dataset.read) + '/read').then(function () { renderPane('notifications'); refreshBell(); }, function (err) { toast(err.message, 'err'); });
          if (all) S.api('POST', '/notifications/read-all').then(function () { renderPane('notifications'); refreshBell(); }, function (err) { toast(err.message, 'err'); });
          if (e.target.closest('[data-reload]')) renderPane('notifications');
        };
      });
    }
  };

  /* ---- settings */
  PANES.settings = {
    title: 'Settings',
    render: function (el) {
      return Promise.all([loadMe(), S.api('GET', '/brain/health').catch(function () { return null; }), S.api('GET', '/worker/health/details').catch(function () { return null; })]).then(function (res) {
        var p = state.profile || {}, brain = res[1], worker = res[2];
        var providers = brain ? Object.keys(brain).map(function (k) { return { name: k, ok: !!(brain[k] && brain[k].available), err: brain[k] && brain[k].last_error }; }) : [];
        var anyAi = providers.some(function (x) { return x.ok; });
        el.innerHTML = '<form class="card" id="setForm"><h3>Your profile</h3>' +
          fieldRow('sn', 'Name', '<input id="sn" type="text" maxlength="200" value="' + esc(p.name || '') + '">') +
          fieldRow('sa', 'Where you live', '<input id="sa" type="text" maxlength="1000" value="' + esc(p.address || '') + '">') +
          fieldRow('sg', 'Age', '<input id="sg" type="number" min="1" max="120" value="' + esc(p.age || '') + '">') +
          fieldRow('si', 'What you want SAGE to help with', '<textarea id="si" rows="3" maxlength="2000">' + esc(p.help_intent || '') + '</textarea>') +
          '<button type="submit" class="btn primary small">Save profile</button>' +
          (p.onboarding_completed ? '' : '<p class="fine">Your first-time setup is not finished. <button type="button" class="linkbtn" id="finishOb">Finish it now</button></p>') + '</form>' +
          '<div class="card"><h3>SAGE server</h3><ul class="list">' +
          '<li><span>Server<small>' + esc(S.base) + '</small></span><span class="tag ok">Connected</span></li>' +
          '<li><span>Background worker</span>' + (worker ? '<span class="tag ' + (worker.worker && worker.worker.running ? 'ok' : 'fail') + '">' + (worker.worker && worker.worker.running ? 'Running' : 'Stopped') + '</span>' : '<span class="tag">Unknown</span>') + '</li>' +
          '<li><span>AI providers<small>' + (anyAi ? 'At least one is working.' : 'None is working yet. Add an AI key on the server.') + '</small></span><span class="tag ' + (anyAi ? 'ok' : 'fail') + '">' + (anyAi ? 'Ready' : 'Not ready') + '</span></li>' +
          providers.map(function (x) { return '<li><span>' + esc(x.name) + (x.err && !x.ok ? '<small>' + esc(String(x.err).slice(0, 120)) + '</small>' : '') + '</span><span class="tag ' + (x.ok ? 'ok' : '') + '">' + (x.ok ? 'Available' : 'Off') + '</span></li>'; }).join('') +
          '</ul></div>' +
          '<div class="card"><h3>Rules that never change</h3><p class="muted">SAGE asks before it spends, posts or sends anything. Spark spending always follows your limits, and every spend needs your approval.</p></div>' +
          '<div class="card"><button type="button" class="btn" id="signOut2">Sign out</button></div>';
        $('setForm').addEventListener('submit', function (e) {
          e.preventDefault();
          var body = { name: $('sn').value.trim() || undefined, address: $('sa').value.trim() || undefined, help_intent: $('si').value.trim() || undefined };
          var age = Number($('sg').value);
          if ($('sg').value) { if (!(age >= 1 && age <= 120) || Math.floor(age) !== age) return toast('Age must be a whole number from 1 to 120.', 'err'); body.age = age; }
          S.api('PATCH', '/identity/me', body).then(function (r) { state.profile = r.profile; $('accName').textContent = displayName(); toast('Profile saved.', 'ok'); }, function (err) { toast(err.message, 'err'); });
        });
        if ($('finishOb')) $('finishOb').addEventListener('click', function () { closePane(); startOnboarding(); });
        $('signOut2').addEventListener('click', function () { S.signOut(); });
        el.onclick = function (e) { if (e.target.closest('[data-reload]')) renderPane('settings'); };
      });
    }
  };

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (!pane.hidden) closePane(); closeRail(); }
  });

  init();
})();
