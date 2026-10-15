/* SAGE web interface (preview). Replies are scripted examples: there is no backend call on this page.
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

  /* ------------------------------------------------------------ example data */
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

  var memoryItems = [
    { text: 'Prefers short, direct answers', status: 'pending' },
    { text: 'Working on a personal AI project called Sage', status: 'pending' },
    { text: 'Based in Nepal, so prefers free tools', status: 'pending' }
  ];
  var learnAllowed = true;

  var ICONS = {
    chat: '<path d="M4 5h16v10H9l-5 4z"/>',
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
    { id: 'research', label: 'Research', keys: ['research', 'look up', 'find out', 'sources', 'search'] },
    { id: 'tasks', label: 'Tasks', keys: ['task', 'to-do', 'todo', 'work queue', 'running'] },
    { id: 'projects', label: 'Projects', keys: ['project'] },
    { id: 'memory', label: 'Memory', keys: ['memory', 'remember', 'know about me'] },
    { id: 'evolution', label: 'Evolution', keys: ['evolution', 'rank', 'tier', 'level'] },
    { id: 'wallet', label: 'Spark wallet', keys: ['spark', 'balance', 'wallet', 'credit', 'rupee', 'npr', 'money', 'earn'] },
    { id: 'market', label: 'Marketplace and jobs', keys: ['market', 'jobs', 'job', 'vacanc', 'rent', 'land', 'property'] },
    { id: 'learning', label: 'Learning', keys: ['learn', 'course', 'study', 'lesson'] },
    { id: 'settings', label: 'Settings', keys: ['setting', 'theme', 'privacy', 'preferences'] }
  ];
  function featureById(id) { return FEATURES.filter(function (f) { return f.id === id; })[0]; }

  var HISTORY = [
    { title: 'Best time to visit Nepal', a: 'October to November is the clearest season for mountain views, and March to May is best for rhododendrons.' },
    { title: 'Plan this week for OROE', a: 'Here is a draft week. Tell me which days are fixed and I will fill in the rest.' },
    { title: 'Explain the Spend Trust Ladder', a: 'SAGE earns first. Part of its earnings is locked as savings, one spend is a small share of earnings, and you approve every spend.' }
  ];

  /* ------------------------------------------------------------------ views */
  var signin = $('signin'), shell = $('shell'), feed = $('feed'), inner = $('feedInner');
  var input = $('input'), sendBtn = $('sendBtn'), pane = $('pane'), paneBody = $('paneBody');
  var current = null; // open feature id
  var busy = false;

  var toastTimer = null;
  function toast(text, kind) {
    var t = document.getElementById('toast');
    if (!t) { t = document.createElement('div'); t.id = 'toast'; t.setAttribute('role', 'status'); t.setAttribute('aria-live', 'polite'); document.body.appendChild(t); }
    t.className = 'toast show ' + (kind || 'ok');
    t.textContent = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, 4000);
  }
  function enter(mode) {
    $('accMode').textContent = mode;
    signin.hidden = true;
    shell.hidden = false;
    renderNav();
    newChat();
    input.focus();
    toast('Signed in (' + (mode.indexOf('Google') === 0 ? 'Google, simulated' : 'private owner mode') + '). Nothing was sent anywhere.', 'ok');
  }
  $('googleBtn').addEventListener('click', function () { enter('Signed in with Google (simulated)'); });
  $('ownerBtn').addEventListener('click', function () { enter('Private mode'); });

  function renderNav() {
    $('nav').innerHTML = FEATURES.map(function (f) {
      return '<li><button type="button" data-feature="' + f.id + '"><svg viewBox="0 0 24 24" aria-hidden="true">' +
        ICONS[f.id === 'market' ? 'market' : f.id] + '</svg><span>' + esc(f.label) + '</span></button></li>';
    }).join('');
    $('history').innerHTML = HISTORY.map(function (h, i) {
      return '<li><button type="button" data-history="' + i + '" title="' + esc(h.title) + '">' + esc(h.title) + '</button></li>';
    }).join('');
    syncNav();
  }
  function syncNav() {
    Array.prototype.forEach.call($('nav').querySelectorAll('button'), function (b) {
      if (b.dataset.feature === current) b.setAttribute('aria-current', 'true'); else b.removeAttribute('aria-current');
    });
  }

  function closeRail() { shell.classList.remove('rail-open'); $('scrim').hidden = true; }
  $('menuBtn').addEventListener('click', function () { shell.classList.add('rail-open'); $('scrim').hidden = false; });
  $('scrim').addEventListener('click', closeRail);

  $('nav').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-feature]');
    if (!b) return;
    openFeature(b.dataset.feature);
    closeRail();
  });
  $('history').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-history]');
    if (!b) return;
    var h = HISTORY[Number(b.dataset.history)];
    clearFeed();
    $('chatTitle').textContent = h.title;
    addMsg('you', h.title);
    addMsg('sage', h.a);
    closeRail();
  });
  $('newChat').addEventListener('click', function () { newChat(); closeRail(); });
  $('paneClose').addEventListener('click', closePane);

  function newChat() {
    clearFeed();
    $('chatTitle').textContent = 'New chat';
    var w = document.createElement('div');
    w.className = 'welcome';
    w.id = 'welcome';
    w.innerHTML = '<h2>What are we working on?</h2>' +
      '<div class="suggest">' +
      '<button type="button" data-q="Research the best time to visit Nepal"><b>Research</b><small>Best time to visit Nepal</small></button>' +
      '<button type="button" data-q="Open my Spark wallet"><b>Spark wallet</b><small>Balance and spend limit</small></button>' +
      '<button type="button" data-q="What is my Evolution rank?"><b>Evolution</b><small>Where you are on the 13 ranks</small></button>' +
      '<button type="button" data-q="Run an ad for 15 Spark"><b>Ask SAGE to act</b><small>See how approval works</small></button>' +
      '</div>';
    inner.appendChild(w);
  }
  function clearFeed() { inner.innerHTML = ''; }
  inner.addEventListener('click', function (e) {
    var s = e.target.closest('button[data-q]');
    if (s) { send(s.dataset.q); return; }
    var c = e.target.closest('button[data-open]');
    if (c) { openFeature(c.dataset.open); return; }
  });

  function scrollDown() { feed.scrollTop = feed.scrollHeight; }
  function addMsg(who, text, extraHtml) {
    var w = $('welcome'); if (w) w.remove();
    var el = document.createElement('div');
    el.className = 'msg ' + who;
    el.innerHTML = '<span class="who" aria-hidden="true">' + (who === 'sage' ? '' : 'You') + '</span><div class="body"><div class="text"></div></div>';
    el.querySelector('.text').textContent = text || '';
    if (extraHtml) el.querySelector('.body').insertAdjacentHTML('beforeend', extraHtml);
    inner.appendChild(el);
    scrollDown();
    return el;
  }

  /* --------------------------------------------------------- understanding */
  function detectFeature(t) {
    for (var i = 0; i < FEATURES.length; i++) {
      for (var k = 0; k < FEATURES[i].keys.length; k++) {
        if (t.indexOf(FEATURES[i].keys[k]) !== -1) return FEATURES[i].id;
      }
    }
    return null;
  }
  var ACTION_RE = /\b(run|launch|start)\b.*\b(ad|ads|campaign)\b|\b(spend|pay|post|publish|send|delete|buy)\b/;

  function reply(text) {
    var t = text.toLowerCase();
    var acts = ACTION_RE.test(t);
    var feat = detectFeature(t);

    if (acts && !/^(open|show|go to)\b/.test(t)) {
      var m = t.match(/(\d[\d,]*)\s*(spark)?/);
      var amount = m ? Number(m[1].replace(/,/g, '')) : 15;
      var what = /ad|campaign/.test(t) ? 'Run a Meta ad campaign' : /post|publish/.test(t) ? 'Publish a post' : /send/.test(t) ? 'Send a message' : /delete/.test(t) ? 'Delete data' : 'Spend Spark';
      return { text: 'I can prepare that, but I will not do it until you approve. Here is what I would do.', approval: { what: what, amount: amount } };
    }
    if (feat === 'research' && !/^(open|show|go to|take me)\b/.test(t)) {
      var q = text.replace(/^(please\s+)?(research|look up|find out about|find out)\s*/i, '').trim() || 'your topic';
      return { text: 'Starting a research run on "' + q + '". The workspace shows how a finished run looks: sources found, which were verified, and the key points.', open: 'research', query: q };
    }
    if (feat) {
      var f = featureById(feat);
      var intro = {
        wallet: 'Here is your Spark wallet. 1 Spark is NPR 1.',
        evolution: 'You are on Evolution 01, Bronze, at Mid intensity. The workspace shows the 13 ranks.',
        tasks: 'Here are your tasks. Each one shows its state: pending, running, completed or failed.',
        projects: 'Here are your projects.',
        memory: 'These are things I may have learned. I only keep what you approve.',
        market: 'Opening Marketplace and jobs.',
        learning: 'Opening Learning.',
        settings: 'Opening Settings.',
        research: 'Opening Research.'
      }[feat];
      return { text: intro, open: feat, label: f.label };
    }
    if (/^(hi|hello|hey|namaste)\b/.test(t)) {
      return { text: 'Namaste. Tell me what you want to get done, or say where you want to go: research, tasks, projects, memory, Evolution, Spark wallet, marketplace, learning or settings.' };
    }
    return { text: 'This page shows the interface with scripted replies, so I cannot answer that yet. In the live SAGE this goes to the research and command engine.\n\nTry: "open research", "show my Spark balance", "what is my Evolution rank?" or "run an ad for 15 Spark".' };
  }

  function approvalHtml(a) {
    var lim = spendLimit(wallet.balance, wallet.earned);
    var within = a.amount > 0 && a.amount <= lim.limit;
    var id = 'ap' + Date.now();
    return '<div class="approval" id="' + id + '" data-amount="' + a.amount + '">' +
      '<h4>Approval needed</h4>' +
      '<dl><dt>Action</dt><dd>' + esc(a.what) + '</dd>' +
      '<dt>Cost</dt><dd>' + fmt(a.amount) + ' Spark (NPR ' + fmt(a.amount * NPR_PER_SPARK) + ')</dd>' +
      '<dt>Your limit per spend</dt><dd>' + fmt(lim.limit) + ' Spark</dd>' +
      '<dt>Check</dt><dd>' + (within ? 'Within your limit' : 'Above your limit, SAGE cannot propose this') + '</dd></dl>' +
      '<div class="row">' +
      (within ? '<button type="button" class="btn small primary" data-approve="' + id + '">Approve</button>' : '') +
      '<button type="button" class="btn small" data-decline="' + id + '">Decline</button></div>' +
      '<p class="fine">Preview only. Approving here does not spend anything.</p></div>';
  }
  inner.addEventListener('click', function (e) {
    var ap = e.target.closest('button[data-approve]');
    var de = e.target.closest('button[data-decline]');
    var b = ap || de;
    if (!b) return;
    var box = $(b.dataset.approve || b.dataset.decline);
    var row = box.querySelector('.row');
    row.outerHTML = '<p class="result">' + (ap ? 'Approved. In the live SAGE the action would run now. Nothing was spent in this preview.' : 'Declined. Nothing happens.') + '</p>';
  });

  /* ------------------------------------------------------------- sending */
  function setBusy(v) { busy = v; sendBtn.disabled = v || !input.value.trim(); }
  function send(text) {
    text = (text || '').trim();
    if (!text || busy) return;
    if (text.length > 2000) { toast('That message is too long. Keep it under 2,000 characters.', 'err'); return; }
    addMsg('you', text);
    if ($('chatTitle').textContent === 'New chat') $('chatTitle').textContent = text.length > 38 ? text.slice(0, 38) + '…' : text;
    input.value = '';
    autosize();
    setBusy(true);
    var r = reply(text);
    var holder = addMsg('sage', '');
    var textEl = holder.querySelector('.text');
    textEl.innerHTML = '<span class="typing" aria-label="SAGE is thinking"><i></i><i></i><i></i></span>';
    window.setTimeout(function () {
      textEl.textContent = '';
      var words = r.text.split(/(\s+)/), i = 0;
      function finish() {
        textEl.textContent = r.text;
        var body = holder.querySelector('.body');
        if (r.approval) body.insertAdjacentHTML('beforeend', approvalHtml(r.approval));
        if (r.open) {
          body.insertAdjacentHTML('beforeend', '<div class="chips"><button type="button" class="chip-link" data-open="' + r.open + '">Opened ' +
            esc(featureById(r.open).label) + '</button></div>');
          openFeature(r.open, r.query);
        }
        setBusy(false);
        scrollDown();
      }
      if (reduceMotion) { finish(); return; }
      var timer = window.setInterval(function () {
        textEl.textContent += words[i++] || '';
        scrollDown();
        if (i >= words.length) { window.clearInterval(timer); finish(); }
      }, 22);
    }, reduceMotion ? 0 : 550);
  }

  function autosize() { input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 144) + 'px'; }
  input.addEventListener('input', function () { autosize(); sendBtn.disabled = busy || !input.value.trim(); });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(input.value); }
  });
  $('composer').addEventListener('submit', function (e) { e.preventDefault(); send(input.value); });

  /* --------------------------------------------------------------- voice */
  var recog = null;
  var mic = $('micBtn');
  function systemLine(t) {
    var el = document.createElement('p');
    el.className = 'fine';
    el.style.textAlign = 'center';
    el.textContent = t;
    inner.appendChild(el);
    scrollDown();
  }
  mic.addEventListener('click', function () {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (recog) { recog.stop(); return; }
    if (!SR) { systemLine('Voice input is not available in this browser or preview. Type your message instead.'); return; }
    try {
      recog = new SR();
      recog.lang = 'en-US';
      recog.interimResults = false;
      recog.onresult = function (ev) { var t = ev.results[0][0].transcript; input.value = t; autosize(); send(t); };
      recog.onerror = function () { systemLine('SAGE could not hear you. Check microphone access, or type your message.'); };
      recog.onend = function () { recog = null; mic.setAttribute('aria-pressed', 'false'); };
      recog.start();
      mic.setAttribute('aria-pressed', 'true');
    } catch (err) {
      recog = null;
      systemLine('Voice input could not start here. Type your message instead.');
    }
  });

  /* ---------------------------------------------------------- workspace */
  function openFeature(id, query) {
    current = id;
    $('paneTitle').textContent = featureById(id).label;
    paneBody.innerHTML = PANELS[id](query);
    pane.hidden = false;
    shell.classList.add('with-pane');
    paneBody.scrollTop = 0;
    syncNav();
    if (id === 'market') bindMarket();
  }
  function closePane() {
    current = null;
    pane.hidden = true;
    shell.classList.remove('with-pane');
    syncNav();
  }
  var EX = '<p class="example-note">Example data. Your real items appear here once the app is connected.</p>';

  var PANELS = {
    research: function (q) {
      return '<div class="card"><label class="fine" for="rq">Question</label>' +
        '<div class="field"><input id="rq" type="text" value="' + esc(q || 'Best time to visit Nepal') + '" readonly></div></div>' +
        '<div class="card"><div class="row-between"><h3>Research complete</h3><span class="tag ok">Done</span></div>' +
        '<p class="muted">Sources found 12, verified 7. October to November and March to May are the clearest seasons for most travellers.</p>' +
        '<ul class="list"><li><span>Accurate and relevant information<small>Checked against several sources</small></span><span class="tag ok">Yes</span></li>' +
        '<li><span>Key points summarised</span><span class="tag ok">Yes</span></li>' +
        '<li><span>Sources provided</span><span class="tag ok">12</span></li></ul></div>' + EX;
    },
    tasks: function () {
      return '<ul class="list">' +
        '<li><span>Draft week plan<small>Started 10 minutes ago</small></span><span class="tag blue">Running</span></li>' +
        '<li><span>Research Kathmandu cafes<small>Waiting for a worker</small></span><span class="tag">Pending</span></li>' +
        '<li><span>Summarise supplier notes<small>Finished today</small></span><span class="tag ok">Completed</span></li>' +
        '<li><span>Fetch competitor site<small>Site blocked the request. Retry or skip.</small></span><span class="tag fail">Failed</span></li></ul>' + EX;
    },
    projects: function () {
      return '<ul class="list">' +
        '<li><span>OROE clothing brand<small>Brand, content and launch plan</small></span><span class="tag blue">Active</span></li>' +
        '<li><span>Dhun Barsa Music<small>YouTube and release schedule</small></span><span class="tag blue">Active</span></li>' +
        '<li><span>First customer demo<small>Research, video and outreach draft</small></span><span class="tag">Planned</span></li></ul>' + EX;
    },
    memory: function () {
      var rows = memoryItems.map(function (m, i) {
        var right = m.status === 'pending'
          ? '<span class="row" style="display:flex;gap:.4rem"><button type="button" class="btn small primary" data-mem="keep" data-i="' + i + '">Keep</button><button type="button" class="btn small" data-mem="reject" data-i="' + i + '">Reject</button></span>'
          : '<span class="tag ' + (m.status === 'kept' ? 'ok' : 'fail') + '">' + (m.status === 'kept' ? 'Kept' : 'Rejected') + '</span>';
        return '<li><span>' + esc(m.text) + '</span>' + right + '</li>';
      }).join('');
      return '<div class="card"><h3>Waiting for your review</h3><p class="muted">SAGE keeps a memory only after you approve it. Nothing here is saved on its own.</p></div><ul class="list">' + rows + '</ul>' + EX;
    },
    evolution: function () {
      var r = RANKS[evo.rank], n = RANKS[evo.rank + 1];
      var chips = RANKS.map(function (x, i) {
        return '<span class="' + (i === evo.rank ? 'on' : '') + '" style="--c:' + x[1] + '"><i></i>' + (i + 1) + ' ' + esc(x[0]) + '</span>';
      }).join('');
      return '<div class="card"><div class="row-between"><h3>Evolution 01: ' + r[0] + '</h3><span class="tag blue">' + evo.level + '</span></div>' +
        '<div class="bar" role="progressbar" aria-valuenow="' + evo.progress + '" aria-valuemin="0" aria-valuemax="100"><i style="width:' + evo.progress + '%"></i></div>' +
        '<p class="muted">' + evo.progress + '% of the way to ' + n[0] + '. Rank comes from verified skill and achievement, and spending Spark never lowers it.</p></div>' +
        '<div class="card"><h3>The 13 Evolutions</h3><div class="ranks">' + chips + '</div></div>' +
        '<div class="card"><h3>Two paths</h3><p class="muted"><b>Skill</b> changes how SAGE looks and who it is. <b>Money</b> changes what it is allowed to do.</p></div>' + EX;
    },
    wallet: function () {
      var lim = spendLimit(wallet.balance, wallet.earned);
      return '<div class="card"><span class="fine">Spark balance</span><div class="big-gold num">' + fmt(wallet.balance) + '</div>' +
        '<p class="muted">= NPR ' + fmt(wallet.balance * NPR_PER_SPARK) + ' (1 Spark = NPR 1)</p>' +
        '<div class="row-between"><span class="fine">Earned ' + fmt(wallet.earned) + '</span><span class="fine">Spent ' + fmt(wallet.spent) + '</span></div></div>' +
        '<div class="card"><h3>Spend limit</h3><p class="muted">Money level: ' + esc(lim.level) + '. ' + fmt(lim.locked) + ' Spark is locked as savings. SAGE may propose up to <b class="num">' + fmt(lim.limit) + ' Spark</b> in one spend, and you approve each one.</p></div>' +
        '<div class="card"><h3>Premium work</h3><ul class="list">' +
        '<li><span>Enhanced Verification</span><b class="num">15 Spark</b></li><li><span>Premium Content Work</span><b class="num">20 Spark</b></li>' +
        '<li><span>Deep Research</span><b class="num">25 Spark</b></li><li><span>Heavy Mission</span><b class="num">50 Spark</b></li></ul></div>' +
        '<div class="card"><span class="tag fail" style="width:max-content">Cash-out is not available yet</span><p class="fine">Paying out rupees needs a payment provider, an owner switch and a legal review.</p></div>' + EX;
    },
    market: function () {
      return '<div class="chips" id="mkChips" role="group" aria-label="Category">' +
        ['Buy', 'Sell', 'Jobs', 'Rent', 'Land'].map(function (c, i) {
          return '<button type="button" class="chip-link" data-mk="' + c + '" aria-pressed="' + (i === 2) + '">' + c + '</button>';
        }).join('') + '</div><ul class="list" id="mkList"></ul>' + EX;
    },
    learning: function () {
      return '<ul class="list">' +
        '<li><span>Digital marketing basics<small>8 modules</small></span><span class="tag blue">3 of 8</span></li>' +
        '<li><span>Video editing for reels<small>6 modules</small></span><span class="tag">Not started</span></li>' +
        '<li><span>English for business<small>10 modules</small></span><span class="tag ok">Done</span></li></ul>' + EX;
    },
    settings: function () {
      return '<div class="card"><div class="switch"><span>Ask before acting<small class="fine" style="display:block">Always on. SAGE never spends, posts or sends without you.</small></span><input type="checkbox" checked disabled aria-label="Ask before acting"></div>' +
        '<div class="switch"><span>Apply spend limits<small class="fine" style="display:block">Always on.</small></span><input type="checkbox" checked disabled aria-label="Apply spend limits"></div>' +
        '<div class="switch"><span>Learn from my chats<small class="fine" style="display:block">SAGE suggests memories and asks first.</small></span><input type="checkbox" id="learnSwitch" ' + (learnAllowed ? 'checked' : '') + ' aria-label="Learn from my chats"></div></div>' +
        '<p class="fine" id="settingNote">Settings change on this page only.</p>';
    }
  };

  var LISTINGS = {
    Buy: [['Honda Dio scooter', 'NPR 125,000', 'Kathmandu'], ['iPhone 14', 'NPR 65,000', 'Lalitpur']],
    Sell: [['Sell something', 'Add a photo and a price', 'Takes a minute']],
    Jobs: [['Frontend developer', 'NPR 60K to 80K a month', 'Kathmandu, full-time'], ['Graphic designer', 'NPR 30K to 45K a month', 'Lalitpur, hybrid'], ['IT support specialist', 'NPR 35K to 50K a month', 'Pokhara']],
    Rent: [['2 bedroom flat', 'NPR 28,000 a month', 'Baneshwor']],
    Land: [['5 aana plot', 'NPR 6,500,000', 'Pokhara']]
  };
  function bindMarket() {
    function show(cat) {
      Array.prototype.forEach.call($('mkChips').children, function (b) { b.setAttribute('aria-pressed', String(b.dataset.mk === cat)); });
      $('mkList').innerHTML = LISTINGS[cat].map(function (r) {
        return '<li><span>' + esc(r[0]) + '<small>' + esc(r[2]) + '</small></span><b class="num">' + esc(r[1]) + '</b></li>';
      }).join('');
    }
    $('mkChips').addEventListener('click', function (e) { var b = e.target.closest('button[data-mk]'); if (b) show(b.dataset.mk); });
    show('Jobs');
  }
  paneBody.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-mem]');
    if (!b) return;
    memoryItems[Number(b.dataset.i)].status = b.dataset.mem === 'keep' ? 'kept' : 'rejected';
    paneBody.innerHTML = PANELS.memory();
  });
  paneBody.addEventListener('change', function (e) {
    if (e.target.id === 'learnSwitch') {
      learnAllowed = e.target.checked;
      $('settingNote').textContent = learnAllowed ? 'SAGE may suggest memories and will ask first. Settings change on this page only.' : 'SAGE will not suggest memories. Settings change on this page only.';
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (!pane.hidden) closePane(); closeRail(); }
  });
})();
