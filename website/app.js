/* SAGE ONE website: Evolution explorer, Spark converter, spend-limit calculator.
   The Spark rate and the spend-limit rules mirror economy/currency.py and economy/spend_ladder.py. */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var $ = function (id) { return document.getElementById(id); };
  function wholeNumber(value) {
    var n = Math.floor(Number(value));
    if (!isFinite(n) || n < 0) return 0;
    return Math.min(n, 1e12);
  }
  function fmt(n) { return Number(n).toLocaleString('en-US'); }

  /* ------------------------------------------------------------------ Spark */
  var NPR_PER_SPARK = 1;
  var sparkIn = $('sparkIn');
  var nprIn = $('nprIn');
  if (sparkIn && nprIn) {
    sparkIn.addEventListener('input', function () {
      nprIn.value = wholeNumber(sparkIn.value) * NPR_PER_SPARK;
    });
    nprIn.addEventListener('input', function () {
      sparkIn.value = Math.floor(wholeNumber(nprIn.value) / NPR_PER_SPARK);
    });
  }

  /* ----------------------------------------------------------- Spend limits */
  var LADDER = [['Bronze', 'Low', 1], ['Bronze', 'Mid', 10], ['Bronze', 'High', 50]];
  var PERCENT_BANDS = [[100, 10], [1000, 5], [10000, 2]];
  var PERCENT_ABOVE = 1;
  var CEILING = 200;

  function levelFor(life) {
    var reached = null;
    LADDER.forEach(function (row) { if (life >= row[2]) reached = row; });
    return reached;
  }
  function percentFor(life) {
    for (var i = 0; i < PERCENT_BANDS.length; i++) {
      if (life <= PERCENT_BANDS[i][0]) return PERCENT_BANDS[i][1];
    }
    return PERCENT_ABOVE;
  }
  function spendLimit(balance, life) {
    var reached = levelFor(life);
    if (!reached) return { level: null, locked: 0, pool: 0, percent: 0, percentCap: 0, limit: 0 };
    var threshold = reached[2];
    var pool = Math.max(0, balance - threshold);
    var percent = percentFor(life);
    var percentCap = Math.floor(life * percent / 100);
    return {
      level: reached[0] + ' ' + reached[1],
      locked: Math.min(balance, threshold),
      pool: pool,
      percent: percent,
      percentCap: percentCap,
      limit: Math.min(pool, percentCap, CEILING)
    };
  }
  window.sageSpendLimit = spendLimit;

  var lifeIn = $('lifeIn'), balIn = $('balIn'), askIn = $('askIn');
  function renderLadder() {
    if (!lifeIn) return;
    var life = wholeNumber(lifeIn.value);
    var bal = wholeNumber(balIn.value);
    var ask = wholeNumber(askIn.value);
    var r = spendLimit(bal, life);

    var rows = [
      { name: 'Above locked savings', value: r.pool },
      { name: 'Share of earnings' + (r.level ? ' (' + r.percent + '%)' : ''), value: r.percentCap },
      { name: 'Ceiling', value: CEILING }
    ];
    var smallest = Math.min(rows[0].value, rows[1].value, rows[2].value);
    var top = Math.max(rows[0].value, rows[1].value, rows[2].value, 1);
    var minTaken = false;
    $('ladderBars').innerHTML = rows.map(function (row) {
      var isMin = !minTaken && row.value === smallest;
      if (isMin) minTaken = true;
      return '<div class="bar-row' + (isMin ? ' min' : '') + '"><span>' + row.name +
        '</span><span class="track"><span class="fill" style="width:' + Math.round(row.value / top * 100) +
        '%"></span></span><b>' + fmt(row.value) + '</b></div>';
    }).join('');

    var verdict = $('verdict');
    var head = '<div class="limit-big">' + fmt(r.limit) + ' Spark</div>' +
      '<div class="muted">Most SAGE may propose in one spend (NPR ' + fmt(r.limit * NPR_PER_SPARK) + '). The smallest of the three lines above.</div>';
    var line;
    verdict.className = 'verdict';
    if (ask <= 0) {
      line = 'Enter an amount above 0 to test a spend.';
    } else if (ask > r.limit) {
      verdict.className = 'verdict no';
      line = 'SAGE cannot propose ' + fmt(ask) + ' Spark. It is above the limit.';
    } else {
      verdict.className = 'verdict ok';
      line = 'SAGE may show you a ' + fmt(ask) + ' Spark spend. It happens only if you approve it.';
    }
    verdict.innerHTML = head + '<p style="margin-top:.6rem"><b>' + line + '</b></p>';

    $('levelLine').textContent = r.level
      ? 'Level reached: ' + r.level + '. ' + fmt(r.locked) + ' Spark is locked as savings and cannot be spent. Every spend needs your approval.'
      : 'Nothing earned yet, so nothing can be spent. Every spend will still need your approval.';
  }
  [lifeIn, balIn, askIn].forEach(function (el) { if (el) el.addEventListener('input', renderLadder); });
  renderLadder();

  /* ------------------------------------------------------ Evolution explorer */
  var RANKS = [
    { name: 'Bronze', material: 'Copper / Bronze', color: '#c7803f' },
    { name: 'Silver', material: 'Silver / White', color: '#cfd6e4' },
    { name: 'Gold', material: 'Gold', color: '#e9b949' },
    { name: 'Platinum', material: 'Platinum / Ice', color: '#b4dcf2' },
    { name: 'Jade', material: 'Jade green', color: '#35c88a' },
    { name: 'Ruby', material: 'Ruby red', color: '#e0314b' },
    { name: 'Sapphire', material: 'Sapphire blue', color: '#3a73ff' },
    { name: 'Emerald', material: 'Emerald green', color: '#19c26b' },
    { name: 'Diamond Sovereign', material: 'Diamond / White', color: '#eaf6ff' },
    { name: 'Black Opal Realm', material: 'Opalescent', color: '#8c9bff', opal: true },
    { name: 'Painite Core', material: 'Rare-mineral red / orange', color: '#ff5a2e' },
    { name: 'Void Matter', material: 'Cosmic / Void', color: '#9150ff' },
    { name: 'Californium Overlord', material: 'Ultra-rare / Cosmic', color: '#ffd36b', dual: '#9b7cff' }
  ];
  var LEVELS = ['Low', 'Mid', 'High'];
  var LEVEL_TEXT = [
    'Subtle particles, lower glow, gentle accents.',
    'More particles, stronger glow, clearer identity.',
    'Maximum intensity, rich particles, evolution-ready.'
  ];
  var COUNTS = [34, 78, 140];
  var GLOW = [0.35, 0.65, 1];

  var canvas = $('core');
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext('2d');
  var W = canvas.width, H = canvas.height, CX = W / 2, CY = H / 2;
  var CORE_R = W * 0.15;

  var state = { rank: 0, level: 0 };
  var particles = [];
  var frags = [];
  var trans = null; // { start, from, to }
  var rafId = null;

  function hexToRgb(hex) {
    var n = parseInt(hex.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }
  function rgba(rgb, a) { return 'rgba(' + rgb[0] + ',' + rgb[1] + ',' + rgb[2] + ',' + a.toFixed(3) + ')'; }
  function accentFor(rank, index, t) {
    var r = RANKS[rank];
    if (r.opal) {
      var hue = 210 + 90 * Math.sin(t / 1400 + index * 0.4);
      return hslToRgb(hue, 85, 72);
    }
    if (r.dual && index % 3 === 0) return hexToRgb(r.dual);
    return hexToRgb(r.color);
  }
  function hslToRgb(h, s, l) {
    h = ((h % 360) + 360) % 360; s /= 100; l /= 100;
    var a = s * Math.min(l, 1 - l);
    var f = function (n) {
      var k = (n + h / 30) % 12;
      return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))));
    };
    return [f(0), f(8), f(4)];
  }

  function makeParticles(count) {
    var list = [];
    for (var i = 0; i < count; i++) {
      list.push({
        a: Math.random() * Math.PI * 2,
        r: 0.34 + Math.random() * 0.56,
        w: (0.00012 + Math.random() * 0.00042) * (Math.random() < 0.5 ? -1 : 1),
        s: 0.8 + Math.random() * 2.2,
        ph: Math.random() * 6.28,
        i: i
      });
    }
    return list;
  }
  function ease(x) { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); }

  function drawCore(glowBoost, darken) {
    var g = ctx.createRadialGradient(CX, CY, 0, CX, CY, W * 0.5);
    g.addColorStop(0, 'rgba(32,76,255,' + (0.28 + 0.2 * glowBoost) + ')');
    g.addColorStop(0.5, 'rgba(20,50,170,0.10)');
    g.addColorStop(1, 'rgba(4,6,12,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);

    var orb = ctx.createRadialGradient(CX - CORE_R * 0.3, CY - CORE_R * 0.4, CORE_R * 0.1, CX, CY, CORE_R * 1.1);
    orb.addColorStop(0, '#5f94ff');
    orb.addColorStop(0.55, '#1c47d6');
    orb.addColorStop(1, '#081a6e');
    ctx.beginPath();
    ctx.arc(CX, CY, CORE_R, 0, Math.PI * 2);
    ctx.fillStyle = orb;
    ctx.shadowColor = 'rgba(82,217,255,' + (0.5 + 0.4 * glowBoost) + ')';
    ctx.shadowBlur = 26 + 22 * glowBoost;
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(190,225,255,0.85)';
    ctx.stroke();

    ctx.fillStyle = '#f2f7ff';
    ctx.font = '600 ' + Math.round(CORE_R * 0.42) + 'px Michroma, Eurostile, "Segoe UI", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('SAGE', CX, CY + 1);
    if (darken) {
      ctx.fillStyle = 'rgba(4,6,12,' + darken + ')';
      ctx.fillRect(0, 0, W, H);
    }
  }

  function drawRing(rank, level, t, alpha) {
    var rgb = accentFor(rank, 0, t);
    ctx.lineWidth = 1.5 + level * 1.2;
    ctx.strokeStyle = rgba(rgb, (0.35 + 0.25 * level) * alpha);
    ctx.shadowColor = rgba(rgb, 0.9 * alpha);
    ctx.shadowBlur = 8 + 14 * GLOW[level];
    ctx.beginPath();
    ctx.arc(CX, CY, W * 0.31, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(CX, CY, W * 0.4, 0, Math.PI * 2);
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.6;
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.shadowBlur = 0;
  }

  function drawParticles(list, rank, level, t, opts) {
    opts = opts || {};
    var radiusScale = opts.radiusScale || 1;
    var speed = opts.speed || 1;
    var alpha = opts.alpha == null ? 1 : opts.alpha;
    ctx.globalCompositeOperation = 'lighter';
    for (var k = 0; k < list.length; k++) {
      var p = list[k];
      var ang = p.a + t * p.w * speed;
      var rad = (p.r * W * 0.46) * radiusScale * (1 + 0.04 * Math.sin(t / 900 + p.ph));
      var x = CX + Math.cos(ang) * rad;
      var y = CY + Math.sin(ang) * rad;
      var rgb = accentFor(rank, p.i, t);
      var tw = 0.55 + 0.45 * Math.sin(t / 500 + p.ph);
      ctx.beginPath();
      ctx.fillStyle = rgba(rgb, (0.35 + 0.5 * tw) * alpha * (0.55 + 0.45 * GLOW[level]));
      ctx.arc(x, y, p.s * (0.8 + 0.5 * GLOW[level]), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalCompositeOperation = 'source-over';
  }

  function render(now) {
    ctx.clearRect(0, 0, W, H);
    var t = now || 0;
    if (!trans) {
      drawCore(GLOW[state.level], 0);
      drawRing(state.rank, state.level, t, 1);
      drawParticles(particles, state.rank, state.level, t);
      return;
    }
    var p = (now - trans.start) / trans.duration;
    if (p >= 1) { finishTransition(); return render(now); }
    var from = trans.from, to = trans.to;
    var darken = 0, flash = 0;
    if (p < 0.35) {
      var a = ease(p / 0.35);
      drawCore(1 + a, 0);
      drawRing(from, 2, t, 1);
      drawParticles(trans.oldParticles, from, 2, t, { radiusScale: 1 - 0.7 * a, speed: 1 + 9 * a });
    } else if (p < 0.5) {
      darken = 0.55 * ease((p - 0.35) / 0.15);
      drawCore(2, darken);
      drawParticles(trans.oldParticles, from, 2, t, { radiusScale: 0.3, speed: 12, alpha: 1 - ease((p - 0.35) / 0.15) });
    } else {
      var b = (p - 0.5) / 0.5;
      darken = 0.55 * (1 - ease(Math.min(1, b / 0.5)));
      drawCore(1 + (1 - ease(b)), darken);
      var ringR = W * 0.52 * ease(b * 1.6);
      if (b < 0.6) {
        ctx.beginPath();
        ctx.arc(CX, CY, ringR, 0, Math.PI * 2);
        ctx.lineWidth = 6 * (1 - b / 0.6);
        ctx.strokeStyle = 'rgba(255,255,255,' + (0.9 * (1 - b / 0.6)).toFixed(3) + ')';
        ctx.stroke();
      }
      for (var f = 0; f < frags.length; f++) {
        var fr = frags[f];
        var d = ease(b * 1.2) * fr.v;
        var fa = Math.max(0, 1 - b * 1.4);
        ctx.beginPath();
        ctx.fillStyle = rgba(fr.rgb, fa * 0.9);
        ctx.arc(CX + Math.cos(fr.a) * d, CY + Math.sin(fr.a) * d, fr.s, 0, Math.PI * 2);
        ctx.fill();
      }
      var fade = ease((b - 0.25) / 0.6);
      drawRing(to, 0, t, fade);
      drawParticles(trans.newParticles, to, 0, t, { alpha: fade, radiusScale: 0.6 + 0.4 * fade });
    }
    if (!trans.switched && p >= 0.5) {
      trans.switched = true;
      var rr = $('explorer');
      rr.style.setProperty('--accent', RANKS[to].opal ? '#8c9bff' : RANKS[to].color);
    }
  }

  function loop(now) {
    render(now);
    rafId = requestAnimationFrame(loop);
  }
  function startLoop() {
    if (reduceMotion) { render(0); return; }
    if (!rafId) rafId = requestAnimationFrame(loop);
  }
  function redraw() { if (reduceMotion) render(0); }

  function startTransition() {
    var from = state.rank, to = from + 1;
    frags = [];
    var oldRgb = hexToRgb(RANKS[from].color);
    for (var i = 0; i < 46; i++) {
      frags.push({ a: Math.random() * Math.PI * 2, v: W * (0.18 + Math.random() * 0.34), s: 1 + Math.random() * 2.6, rgb: oldRgb });
    }
    trans = {
      start: performance.now(), duration: 3400, from: from, to: to, switched: false,
      oldParticles: particles, newParticles: makeParticles(COUNTS[0])
    };
    setBusy(true);
  }
  function finishTransition() {
    state.rank = trans.to;
    state.level = 0;
    particles = trans.newParticles;
    trans = null;
    frags = [];
    setBusy(false);
    updateUI();
  }

  /* ------------------------------------------------------------------ UI */
  var chipsEl = $('rankChips');
  var segEl = $('levelSeg');
  var evolveBtn = $('evolveBtn');

  function accentColor(rank) { return RANKS[rank].opal ? '#8c9bff' : RANKS[rank].color; }

  RANKS.forEach(function (r, i) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip';
    b.dataset.rank = String(i);
    b.textContent = (i + 1) + ' ' + r.name;
    b.setAttribute('aria-pressed', 'false');
    chipsEl.appendChild(b);
  });

  function setBusy(busy) {
    evolveBtn.disabled = busy || state.rank >= RANKS.length - 1;
    Array.prototype.forEach.call(chipsEl.children, function (c) { c.disabled = busy; });
    Array.prototype.forEach.call(segEl.children, function (c) { c.disabled = busy; });
  }

  function updateUI() {
    var r = RANKS[state.rank];
    var next = RANKS[state.rank + 1];
    $('explorer').style.setProperty('--accent', accentColor(state.rank));
    $('rankTitle').textContent = 'Evolution ' + String(state.rank + 1).padStart(2, '0') + ': ' + r.name;
    $('rankText').textContent = r.material + ' material, ' + LEVELS[state.level] + '. ' + LEVEL_TEXT[state.level];
    $('badgeRank').innerHTML = '<b>Evolution ' + String(state.rank + 1).padStart(2, '0') + '</b> ' + r.name;
    $('badgeLevel').textContent = LEVELS[state.level];
    Array.prototype.forEach.call(chipsEl.children, function (c) {
      c.setAttribute('aria-pressed', String(Number(c.dataset.rank) === state.rank));
    });
    Array.prototype.forEach.call(segEl.children, function (c) {
      c.setAttribute('aria-pressed', String(Number(c.dataset.level) === state.level));
    });
    evolveBtn.disabled = !!trans || !next;
    $('evolveNote').textContent = next
      ? 'Goes from ' + r.name + ' High to ' + next.name + ' Low.'
      : 'This is the final Evolution.';
    particles = makeParticles(COUNTS[state.level]);
    redraw();
  }

  chipsEl.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-rank]');
    if (!b || trans) return;
    state.rank = Number(b.dataset.rank);
    updateUI();
  });
  segEl.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-level]');
    if (!b || trans) return;
    state.level = Number(b.dataset.level);
    updateUI();
  });
  evolveBtn.addEventListener('click', function () {
    if (trans || state.rank >= RANKS.length - 1) return;
    if (state.level !== 2) { state.level = 2; updateUI(); }
    if (reduceMotion) {
      state.rank += 1;
      state.level = 0;
      updateUI();
      return;
    }
    startTransition();
    updateUI();
  });

  updateUI();
  startLoop();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(redraw);
})();
