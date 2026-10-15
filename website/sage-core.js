/* SAGE core: the one place the website talks to the real SAGE server.
   Used by the web app (chat/) and the mobile home (mobile/). Nothing in here is simulated:
   every function calls the server in website/site-config.js (apiBase) and reports what it really answered. */
(function () {
  'use strict';

  var cfg = window.SITE || {};
  var base = String(cfg.apiBase || '').trim().replace(/\/+$/, '');
  var AUTH_KEY = 'sage.auth';
  var listeners = {};

  /* ---------------------------------------------------------------- helpers */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function fmt(n) { return Number(n || 0).toLocaleString('en-US'); }
  function relTime(iso) {
    if (!iso) return '';
    var t = Date.parse(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
    if (isNaN(t)) return '';
    var s = Math.max(0, Math.round((Date.now() - t) / 1000));
    if (s < 60) return 'just now';
    if (s < 3600) return Math.floor(s / 60) + ' min ago';
    if (s < 86400) return Math.floor(s / 3600) + ' h ago';
    return Math.floor(s / 86400) + ' d ago';
  }
  function on(name, fn) { (listeners[name] = listeners[name] || []).push(fn); }
  function emit(name, data) { (listeners[name] || []).forEach(function (fn) { try { fn(data); } catch (e) { /* listener errors never break the app */ } }); }

  /* Small, safe markdown: escapes everything first, then adds bold, code, lists, links (http/https only). */
  function md(src) {
    var text = String(src == null ? '' : src).replace(/\r\n/g, '\n');
    var blocks = [];
    text = text.replace(/```([\s\S]*?)```/g, function (_, code) {
      blocks.push('<pre><code>' + esc(code.replace(/^\w*\n/, '').replace(/\n$/, '')) + '</code></pre>');
      return '\u0000' + (blocks.length - 1) + '\u0000';
    });
    function inline(s) {
      s = esc(s);
      s = s.replace(/`([^`\n]+)`/g, '<code>$1</code>');
      s = s.replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?]|$)/g, '$1<em>$2</em>');
      s = s.replace(/\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
      s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>');
      return s;
    }
    var out = [], lines = text.split('\n'), i = 0;
    while (i < lines.length) {
      var line = lines[i];
      var ph = /^\u0000(\d+)\u0000$/.exec(line.trim());
      if (ph) { out.push(blocks[Number(ph[1])]); i++; continue; }
      if (/^\s*([-*•])\s+/.test(line)) {
        var li = [];
        while (i < lines.length && /^\s*([-*•])\s+/.test(lines[i])) { li.push('<li>' + inline(lines[i].replace(/^\s*([-*•])\s+/, '')) + '</li>'); i++; }
        out.push('<ul>' + li.join('') + '</ul>'); continue;
      }
      if (/^\s*\d+[.)]\s+/.test(line)) {
        var ol = [];
        while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) { ol.push('<li>' + inline(lines[i].replace(/^\s*\d+[.)]\s+/, '')) + '</li>'); i++; }
        out.push('<ol>' + ol.join('') + '</ol>'); continue;
      }
      var h = /^(#{1,3})\s+(.*)$/.exec(line);
      if (h) { out.push('<p><strong>' + inline(h[2]) + '</strong></p>'); i++; continue; }
      if (!line.trim()) { i++; continue; }
      var para = [];
      while (i < lines.length && lines[i].trim() && !/^\s*([-*•]|\d+[.)])\s+/.test(lines[i]) && !/^#{1,3}\s/.test(lines[i]) && !/^\u0000\d+\u0000$/.test(lines[i].trim())) { para.push(inline(lines[i])); i++; }
      out.push('<p>' + para.join('<br>') + '</p>');
    }
    return out.join('');
  }

  /* ------------------------------------------------------------------- auth */
  var memoryAuth = null;
  function getAuth() {
    if (memoryAuth) return memoryAuth;
    try { var raw = sessionStorage.getItem(AUTH_KEY); if (raw) memoryAuth = JSON.parse(raw); } catch (e) { /* storage can be blocked */ }
    return memoryAuth;
  }
  function setAuth(token, kind) {
    memoryAuth = { token: token, kind: kind };
    try { sessionStorage.setItem(AUTH_KEY, JSON.stringify(memoryAuth)); } catch (e) { /* keep in memory only */ }
  }
  function clearAuth() {
    memoryAuth = null;
    try { sessionStorage.removeItem(AUTH_KEY); } catch (e) { /* ignore */ }
  }

  /* -------------------------------------------------------------------- API */
  function ApiError(status, message, code) {
    this.name = 'ApiError';
    this.status = status;
    this.code = code || 'error';
    this.message = message;
  }
  ApiError.prototype = Object.create(Error.prototype);

  function detailText(data) {
    if (!data) return '';
    var d = data.detail !== undefined ? data.detail : data.error;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d.length) {
      var first = d[0] || {};
      var where = Array.isArray(first.loc) ? first.loc.filter(function (x) { return x !== 'body'; }).join('.') : '';
      return (where ? where + ': ' : '') + (first.msg || 'Invalid input.');
    }
    return '';
  }

  function api(method, path, body, opts) {
    opts = opts || {};
    if (!base) {
      return Promise.reject(new ApiError(0, 'The SAGE server address is not set. Add apiBase to site-config.js.', 'no_base'));
    }
    var controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = null;
    if (controller) timer = setTimeout(function () { controller.abort(); }, opts.timeout || 45000);
    var headers = { 'Accept': 'application/json' };
    if (body !== undefined && body !== null) headers['Content-Type'] = 'application/json';
    var auth = getAuth();
    if (auth && !opts.noAuth) headers['Authorization'] = 'Bearer ' + auth.token;
    return fetch(base + path, {
      method: method,
      headers: headers,
      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
      signal: controller ? controller.signal : undefined,
      credentials: 'omit',
      cache: 'no-store'
    }).then(function (res) {
      return res.text().then(function (txt) {
        var data = null;
        try { data = txt ? JSON.parse(txt) : null; } catch (e) { data = null; }
        if (res.ok) return data;
        var msg = detailText(data);
        var status = res.status;
        if (status === 401) {
          if (!opts.noAuth && auth) { clearAuth(); emit('signedout', { reason: 'expired' }); }
          throw new ApiError(401, msg || 'Please sign in again.', 'unauthorized');
        }
        if (status === 403) throw new ApiError(403, msg || 'This account is not allowed to do that.', 'forbidden');
        if (status === 404) throw new ApiError(404, msg || 'Not found.', 'not_found');
        if (status === 413) throw new ApiError(413, 'That is too large to send.', 'too_large');
        if (status === 422) throw new ApiError(422, msg || 'Some of the information is not valid.', 'invalid');
        if (status === 429) throw new ApiError(429, 'Too many requests. Wait a moment and try again.', 'rate_limited');
        if (status === 503) throw new ApiError(503, msg || 'The SAGE server is not ready for that yet.', 'unavailable');
        throw new ApiError(status, status >= 500 ? 'The SAGE server had a problem. Try again in a moment.' : (msg || 'Request failed.'), 'server');
      });
    }, function (err) {
      if (err && err.name === 'AbortError') throw new ApiError(0, 'The SAGE server took too long to answer. If it was asleep it may need a minute, so try again.', 'timeout');
      throw new ApiError(0, 'Cannot reach the SAGE server. Check your internet connection and that the server is running.', 'network');
    }).then(function (v) { if (timer) clearTimeout(timer); return v; }, function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  /* ------------------------------------------------------- Google sign-in */
  var gsiPromise = null;
  function loadGoogle() {
    if (gsiPromise) return gsiPromise;
    gsiPromise = new Promise(function (resolve, reject) {
      if (window.google && window.google.accounts && window.google.accounts.id) return resolve(window.google);
      var s = document.createElement('script');
      s.src = 'https://accounts.google.com/gsi/client';
      s.async = true;
      s.defer = true;
      var t = setTimeout(function () { reject(new Error('timeout')); }, 12000);
      s.onload = function () { clearTimeout(t); window.google && window.google.accounts ? resolve(window.google) : reject(new Error('missing')); };
      s.onerror = function () { clearTimeout(t); reject(new Error('blocked')); };
      document.head.appendChild(s);
    });
    gsiPromise.catch(function () { gsiPromise = null; });
    return gsiPromise;
  }
  function renderGoogleButton(el, clientId, onCredential) {
    return loadGoogle().then(function (google) {
      google.accounts.id.initialize({
        client_id: clientId,
        callback: function (resp) { if (resp && resp.credential) onCredential(resp.credential); },
        auto_select: false,
        cancel_on_tap_outside: true
      });
      el.innerHTML = '';
      google.accounts.id.renderButton(el, { theme: 'filled_black', size: 'large', shape: 'pill', text: 'continue_with', width: Math.min(320, el.clientWidth || 320) });
    });
  }

  function loginWithGoogleCredential(credential) {
    return api('POST', '/identity/google', { id_token: credential }, { noAuth: true }).then(function (data) {
      setAuth(credential, 'google');
      return data;
    });
  }
  function loginDeveloper(label) {
    return api('POST', '/identity/dev-login', { label: label || 'local-owner' }, { noAuth: true }).then(function (data) {
      setAuth(data.token, 'developer');
      return data;
    });
  }
  function signOut() {
    clearAuth();
    try { if (window.google && window.google.accounts) window.google.accounts.id.disableAutoSelect(); } catch (e) { /* ignore */ }
    emit('signedout', { reason: 'user' });
  }

  /* --------------------------------------------------------------- commands */
  function TaskError(message, task) { this.name = 'TaskError'; this.message = message; this.task = task; }
  TaskError.prototype = Object.create(Error.prototype);

  function resultText(task) {
    var r = task && task.result;
    if (r == null || r === '') return '';
    if (typeof r === 'string') {
      var t = r.trim();
      if (t.charAt(0) === '{' || t.charAt(0) === '[') {
        try { r = JSON.parse(t); } catch (e) { return r; }
      } else return r;
    }
    if (typeof r === 'object') {
      var pick = r.final || r.response || r.answer || r.text || r.summary || r.result || r.output;
      if (typeof pick === 'string' && pick) return pick;
      if (pick && typeof pick === 'object') return resultText({ result: pick });
      return '```\n' + JSON.stringify(r, null, 2) + '\n```';
    }
    return String(r);
  }

  function friendlyTaskError(raw) {
    var e = String(raw || '').trim();
    if (!e) return 'SAGE could not finish that.';
    if (/all allowed sage providers failed/i.test(e)) {
      return 'SAGE has no working AI provider yet. The server needs at least one AI key (Gemini, Groq, Cerebras, OpenRouter) or a running local Ollama. Details: ' + e.replace(/\s+/g, ' ');
    }
    return e.replace(/\s+$/, '');
  }

  /* Queue a command on the server and wait for the real result. */
  function sendCommand(message, opts) {
    opts = opts || {};
    var cancelled = false;
    var handle = { cancel: function () { cancelled = true; } };
    var body = { message: message };
    if (opts.sessionId) body.session_id = opts.sessionId;
    if (opts.projectId) body.project_id = opts.projectId;
    handle.promise = api('POST', '/command', body).then(function (queued) {
      var sessionId = queued.session_id;
      var taskId = queued.task && queued.task.id;
      if (opts.onQueued) opts.onQueued({ sessionId: sessionId, task: queued.task });
      var started = Date.now();
      var limit = opts.maxWaitMs || 4 * 60 * 1000;
      return new Promise(function (resolve, reject) {
        var delay = 900;
        function tick() {
          if (cancelled) return reject(new TaskError('Stopped.', null));
          if (Date.now() - started > limit) return reject(new TaskError('SAGE is still working on this. It keeps running in the background: open Tasks to see the result when it finishes.', null));
          api('GET', '/tasks/' + encodeURIComponent(taskId), null, { timeout: 20000 }).then(function (r) {
            var task = r.task || {};
            if (opts.onStatus) opts.onStatus(task);
            if (task.status === 'completed') {
              var text = resultText(task);
              return resolve({ sessionId: sessionId, task: task, text: text || 'Done. SAGE finished without a written answer.' });
            }
            if (task.status === 'failed') return reject(new TaskError(friendlyTaskError(task.error), task));
            if (task.status === 'cancelled') return reject(new TaskError('This was cancelled.', task));
            delay = Math.min(delay + 250, 2500);
            setTimeout(tick, delay);
          }, function (err) {
            if (err instanceof ApiError && (err.code === 'network' || err.code === 'timeout' || err.status >= 500)) {
              setTimeout(tick, 3000); // transient: keep waiting
            } else reject(err);
          });
        }
        setTimeout(tick, 600);
      });
    });
    return handle;
  }

  /* ----------------------------------------------------------------- toast */
  var toastTimer = null;
  function toast(text, kind) {
    var t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      t.setAttribute('role', 'status');
      t.setAttribute('aria-live', 'polite');
      document.body.appendChild(t);
    }
    t.className = 'toast show ' + (kind || 'ok');
    t.textContent = text;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.className = 'toast'; }, kind === 'err' ? 6000 : 3800);
  }

  window.SAGE = {
    base: base,
    esc: esc, fmt: fmt, md: md, relTime: relTime, toast: toast, on: on,
    api: api, ApiError: ApiError, TaskError: TaskError,
    auth: { get: getAuth, clear: clearAuth },
    loadGoogle: loadGoogle, renderGoogleButton: renderGoogleButton,
    loginWithGoogleCredential: loginWithGoogleCredential, loginDeveloper: loginDeveloper, signOut: signOut,
    sendCommand: sendCommand, resultText: resultText
  };
})();
