/*
 * The Tank — Preferences dashboard
 * Vanilla JS, no deps, no framework. Fetches /api/* and PUTs changes back.
 */
(() => {
  'use strict';

  // ─── helpers ────────────────────────────────────────────────────────────

  const TOKEN_KEY = 'tank_personalize_token';

  const storedToken = () => localStorage.getItem(TOKEN_KEY) || '';

  const setToken = (t) => {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  };

  const authHeaders = () => {
    const t = storedToken();
    return t ? { 'Authorization': 'Bearer ' + t } : {};
  };

  const apiGet = async (path) => {
    const r = await fetch(path, { headers: authHeaders() });
    if (!r.ok) throw new Error('GET ' + path + ' -> ' + r.status);
    return r.json();
  };

  const apiPut = async (path, body) => {
    const r = await fetch(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body)
    });
    const text = await r.text();
    let payload = null;
    try { payload = JSON.parse(text); } catch (_) {}
    if (!r.ok) {
      const msg = (payload && payload.detail) || text || r.statusText;
      throw new Error('PUT ' + path + ' -> ' + r.status + ' ' + msg);
    }
    return payload;
  };

  const apiPost = async (path, body) => {
    const r = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body)
    });
    if (!r.ok) throw new Error('POST ' + path + ' -> ' + r.status);
    return r.json();
  };

  const setStatus = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt || '';
  };

  const setText = (id, txt) => {
    const el = document.getElementById(id);
    if (el) el.textContent = txt;
  };

  // ─── tab switching ──────────────────────────────────────────────────────

  const tabs = document.querySelectorAll('.tab');
  const panels = document.querySelectorAll('.panel');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.setAttribute('aria-selected', 'false'));
      tab.setAttribute('aria-selected', 'true');
      panels.forEach(p => p.classList.add('hidden'));
      const id = 'panel-' + tab.dataset.panel;
      const p = document.getElementById(id);
      if (p) p.classList.remove('hidden');
    });
  });

  // ─── persona ────────────────────────────────────────────────────────────

  const personaFields = [
    'p-name', 'p-tz', 'p-tone', 'p-style', 'p-emoji',
    'p-rate', 'p-pitch', 'p-vol', 'p-backstory', 'p-phrases'
  ];

  const loadPersona = async () => {
    try {
      const data = await apiGet('/api/persona');
      const p = data.persona || {};
      setVal('p-name', p.name);
      setVal('p-tz', p.time_zone);
      setVal('p-tone', p.tone);
      setVal('p-style', p.response_style);
      setVal('p-emoji', p.emoji_use);
      setVal('p-rate', p.voice_rate);
      setVal('p-pitch', p.voice_pitch);
      setVal('p-vol', p.voice_volume);
      setVal('p-backstory', p.backstory);
      setVal('p-phrases', (p.signature_phrases || []).join('\n'));
      // Slider readouts
      setText('p-rate-out', (+p.voice_rate).toFixed(2));
      setText('p-pitch-out', (+p.voice_pitch).toFixed(2));
      setText('p-vol-out', (+p.voice_volume).toFixed(2));
      const w = document.getElementById('persona-warnings');
      if (w) {
        w.innerHTML = '';
        (data.warnings || []).forEach(msg => {
          const li = document.createElement('li');
          li.textContent = msg;
          w.appendChild(li);
        });
      }
    } catch (e) {
      setStatus('persona-status', e.message);
    }
  };

  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = (value === undefined || value === null) ? '' : value;
  };

  const pairSlider = (sliderId, outId, fmt) => {
    const slider = document.getElementById(sliderId);
    const out = document.getElementById(outId);
    if (!slider || !out) return;
    const upd = () => {
      out.textContent = fmt(parseFloat(slider.value));
    };
    slider.addEventListener('input', upd);
    upd();
  };

  ['p-rate', 'p-pitch', 'p-vol'].forEach((id, i) => {
    pairSlider(id, id + '-out', v => v.toFixed(2));
  });

  document.getElementById('save-persona').addEventListener('click', async () => {
    const payload = {
      name: val('p-name'),
      time_zone: val('p-tz'),
      tone: val('p-tone'),
      response_style: val('p-style'),
      emoji_use: val('p-emoji'),
      voice_rate: parseFloat(val('p-rate')),
      voice_pitch: parseFloat(val('p-pitch')),
      voice_volume: parseFloat(val('p-vol')),
      backstory: val('p-backstory'),
      signature_phrases: val('p-phrases').split('\n').map(s => s.trim()).filter(Boolean)
    };
    try {
      const r = await apiPut('/api/persona', payload);
      setStatus('persona-status', 'Saved.');
      const w = document.getElementById('persona-warnings');
      if (w) {
        w.innerHTML = '';
        (r.warnings || []).forEach(msg => {
          const li = document.createElement('li');
          li.textContent = msg;
          w.appendChild(li);
        });
      }
    } catch (e) {
      setStatus('persona-status', e.message);
    }
  });

  document.getElementById('reset-persona').addEventListener('click', async () => {
    try {
      await apiPost('/api/persona/reset', {});
      setStatus('persona-status', 'Reset.');
      loadPersona();
    } catch (e) {
      setStatus('persona-status', e.message);
    }
  });

  const val = id => (document.getElementById(id) || {}).value || '';

  // ─── prefs (motion / privacy / audio) ───────────────────────────────────

  const sectionKeys = {
    motion: {
      max_speed_mps: ['m-speed', v => +v.toFixed(2) + ' m/s'],
      turn_speed_radps: ['m-turn', v => +v.toFixed(2) + ' rad/s'],
      follow_distance_m: ['m-follow', v => +v.toFixed(2) + ' m'],
      obstacle_stop_distance_m: ['m-stop', v => +v.toFixed(2) + ' m'],
      enable_chime_on_arrival: null,
      patrol_mode: 'm-patrol'
    },
    privacy: {
      share_recordings: 'pr-share-rec',
      telemetry_to_ai: 'pr-telemetry',
      remember_conversations: 'pr-remember',
      redact_faces_in_recordings: 'pr-blur',
      auto_delete_recordings_days: ['pr-days', v => v + ' days']
    },
    audio: {
      wake_sensitivity: ['a-wake', v => v.toFixed(2)],
      chime_volume: ['a-vol', v => v.toFixed(2)],
      wake_chime: 'a-chime',
      tts_voice: 'a-voice',
      speech_language: 'a-lang'
    }
  };

  const loadPrefs = async () => {
    try {
      const data = await apiGet('/api/prefs');
      Object.keys(sectionKeys).forEach(section => {
        const mapping = sectionKeys[section];
        const values = data[section] || {};
        Object.keys(mapping).forEach(k => {
          const meta = mapping[k];
          if (!meta) return;
          const id = Array.isArray(meta) ? meta[0] : meta;
          const el = document.getElementById(id);
          if (!el) return;
          if (el.type === 'checkbox') {
            el.checked = !!values[k];
          } else {
            el.value = values[k];
            if (Array.isArray(meta)) {
              const out = document.getElementById(id + '-out');
              if (out) out.textContent = meta[1](parseFloat(values[k]));
            }
          }
        });
      });
    } catch (e) {
      setStatus('motion-status', e.message);
      setStatus('privacy-status', e.message);
      setStatus('audio-status', e.message);
    }
  };

  const buildSectionPayload = (section) => {
    const out = {};
    const mapping = sectionKeys[section];
    Object.keys(mapping).forEach(k => {
      const meta = mapping[k];
      if (!meta) return;
      const id = Array.isArray(meta) ? meta[0] : meta;
      const el = document.getElementById(id);
      if (!el) return;
      if (el.type === 'checkbox') out[k] = el.checked;
      else if (el.type === 'range' || el.type === 'number') out[k] = parseFloat(el.value);
      else out[k] = el.value;
    });
    return out;
  };

  ['motion', 'privacy', 'audio'].forEach(section => {
    document.getElementById('save-' + section).addEventListener('click', async () => {
      try {
        await apiPut('/api/prefs/' + section, buildSectionPayload(section));
        setStatus(section + '-status', 'Saved.');
        loadPrefs();
      } catch (e) {
        setStatus(section + '-status', e.message);
      }
    });
    document.getElementById('reset-' + section).addEventListener('click', async () => {
      try {
        await apiPost('/api/prefs/' + section + '/reset', {});
        setStatus(section + '-status', 'Reset.');
        loadPrefs();
      } catch (e) {
        setStatus(section + '-status', e.message);
      }
    });
  });

  // Slider readouts
  ['m-speed', 'm-turn', 'm-follow', 'm-stop', 'a-wake', 'a-vol', 'pr-days'].forEach(id => {
    const meta = [null, 'm-speed-0', 'm-turn-0', 'm-follow-0', 'm-stop-0',
                  'a-wake-0', 'a-vol-0', 'pr-days-0'];
    const out = document.getElementById(id + '-out');
    if (!out) return;
    document.getElementById(id).addEventListener('input', () => {
      const v = parseFloat(document.getElementById(id).value);
      if (id === 'pr-days') out.textContent = v + ' days';
      else if (id === 'm-speed') out.textContent = v.toFixed(2) + ' m/s';
      else if (id === 'm-turn')  out.textContent = v.toFixed(2) + ' rad/s';
      else if (id === 'm-follow' || id === 'm-stop') out.textContent = v.toFixed(2) + ' m';
      else out.textContent = v.toFixed(2);
    });
  });

  // ─── memory ─────────────────────────────────────────────────────────────

  const loadMemory = async () => {
    try {
      const m = await apiGet('/api/persona/memory');
      setVal('mem-name', m.remembered_name || '');
      const last = m.last_seen_ts ? new Date(m.last_seen_ts * 1000)
                                   .toLocaleString() : 'never';
      setText('mem-last', last);
      const factsEl = document.getElementById('mem-facts');
      factsEl.innerHTML = '';
      (m.custom_facts || []).forEach((fact) => {
        const li = document.createElement('li');
        const safe = fact.replace(/"/g, '&quot;');
        li.innerHTML =
          '<span class="fact-text"></span>' +
          '<button class="btn btn-tiny" data-fact="' + safe +
          '" type="button">forget</button>';
        li.querySelector('.fact-text').textContent = fact;
        factsEl.appendChild(li);
      });
      factsEl.querySelectorAll('button[data-i]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const fact = btn.getAttribute('data-fact') || '';
          if (!fact) return;
          try {
            await apiPut('/api/persona/memory', { remove_fact: fact });
            setStatus('mem-status', 'Forgotten.');
            loadMemory();
          } catch (e) { setStatus('mem-status', e.message); }
        });
      });
      const moodsEl = document.getElementById('mem-moods');
      moodsEl.innerHTML = '';
      const moods = m.moods_seen || {};
      Object.keys(moods).sort((a, b) => moods[b] - moods[a])
                        .slice(0, 6).forEach(mood => {
        const li = document.createElement('li');
        li.innerHTML = '<span class="mood-key"></span><span class="mood-cnt"></span>';
        li.querySelector('.mood-key').textContent = mood;
        li.querySelector('.mood-cnt').textContent = '\u00d7' + moods[mood];
        moodsEl.appendChild(li);
      });
    } catch (e) {
      setStatus('mem-status', e.message);
    }
  };

  document.getElementById('mem-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const v = (document.getElementById('mem-new-fact').value || '').trim();
    if (!v) return;
    try {
      await apiPut('/api/persona/memory', { add_fact: v });
      document.getElementById('mem-new-fact').value = '';
      setStatus('mem-status', 'Remembered.');
      loadMemory();
    } catch (e) { setStatus('mem-status', e.message); }
  });

  document.getElementById('mem-clear-facts').addEventListener('click', async () => {
    try {
      await apiPut('/api/persona/memory', { clear_facts: true });
      setStatus('mem-status', 'Cleared.');
      loadMemory();
    } catch (e) { setStatus('mem-status', e.message); }
  });

  document.getElementById('mem-clear-all').addEventListener('click', async () => {
    if (!confirm("Erase ALL memory — including Tank's memory of your name?")) return;
    try {
      await apiPut('/api/persona/memory', { clear_all: true });
      setStatus('mem-status', 'Wiped.');
      loadMemory();
    } catch (e) { setStatus('mem-status', e.message); }
  });

  document.getElementById('mem-touch').addEventListener('click', async () => {
    try {
      await apiPost('/api/persona/memory/touch', {});
      setStatus('mem-status', 'Touched.');
      loadMemory();
    } catch (e) { setStatus('mem-status', e.message); }
  });

  document.getElementById('mem-name').addEventListener('change', async (ev) => {
    const name = (ev.target.value || '').trim();
    try {
      await apiPut('/api/persona/memory', { name: name || null });
      setStatus('mem-status', name ? 'Name saved.' : 'Name cleared.');
      loadMemory();
    } catch (e) { setStatus('mem-status', e.message); }
  });

  // ─── preview ────────────────────────────────────────────────────────────

  const loadPrompt = async () => {
    try {
      const r = await apiGet('/api/prompt');
      setText('prompt-out', r.prompt || '(empty)');
    } catch (e) {
      setText('prompt-out', 'Error: ' + e.message);
    }
  };

  const loadDialogue = async () => {
    try {
      const r = await apiGet('/api/dialogue?reason=wake');
      const ul = document.getElementById('dialogue-out');
      ul.innerHTML = '';
      const items = [
        ['Greeting', r.greeting],
        ['Farewell (idle)', r.farewell],
        ['Missing-name ask', r.missing_name_ask],
        ['Default empathy', r.empathy_prefix]
      ];
      items.forEach(([k, v]) => {
        const li = document.createElement('li');
        li.innerHTML = '<strong></strong><div></div>';
        li.querySelector('strong').textContent = k;
        li.querySelector('div').textContent = v || '(blank)';
        ul.appendChild(li);
      });
      // Acknowledgements
      (r.acknowledgements || []).forEach(line => {
        const li = document.createElement('li');
        li.innerHTML = '<strong>Acknowledgement</strong><div></div>';
        li.querySelector('div').textContent = line;
        ul.appendChild(li);
      });
    } catch (e) {
      setText('dialogue-out', 'Error: ' + e.message);
    }
  };

  document.getElementById('refresh-prompt').addEventListener('click', loadPrompt);
  document.getElementById('refresh-dialogue').addEventListener('click', loadDialogue);

  // ─── auth + bootstrap ───────────────────────────────────────────────────

  document.getElementById('api-token').value = storedToken();
  document.getElementById('auth-save').addEventListener('click', () => {
    setToken(document.getElementById('api-token').value);
    setStatus('auth-status', 'Saved.');
    bootstrap();
  });

  const checkHealth = async () => {
    try {
      const r = await apiGet('/api/health');
      setStatus('auth-status',
        (r.open_mode ? 'open mode' : 'authenticated ' + (r.version || '?')));
      return r;
    } catch (e) {
      setStatus('auth-status', 'unreachable');
      throw e;
    }
  };

  const bootstrap = async () => {
    await checkHealth();
    await Promise.all([
      loadPersona(),
      loadPrefs(),
      loadMemory(),
      loadPrompt(),
      loadDialogue()
    ]).catch(_ => {});
  };

  bootstrap();
})();
