// Shared utilities. Requires CONFIG to be loaded first.

const Utils = (function () {

  // Returns the asset path for a given node label.
  // For main nodes (A–H): looks up the fractal filename assigned to that node in
  // studySessionData (set at consent by assignStimuli).
  // For practice nodes (I–K): falls back to the placeholder stimulus_I.png pattern.
  function getStimulusPath(node) {
    const base = (typeof jatos !== 'undefined' && jatos.studyAssetsUrl)
      ? jatos.studyAssetsUrl
      : '.';
    const map = jatos.studySessionData[CONFIG.sessionKeys.stimulusMap];
    if (map && map[node]) {
      return `${base}/${CONFIG.stimulusDir}/${map[node]}`;
    }
    if (CONFIG.practiceStimuli && CONFIG.practiceStimuli[node]) {
      return `${base}/${CONFIG.stimulusDir}/${CONFIG.practiceStimuli[node]}`;
    }
    return `${base}/${CONFIG.stimulusDir}/stimulus_${node}${CONFIG.stimulusExtension}`;
  }

  // Assigns stimulus config 3 or 4 using the JATOS Batch Session to keep counts
  // balanced across participants via the JATOS Batch Session.
  // Returns a Promise that resolves with the assigned config number (3 or 4).
  function assignStimulusConfig() {
    return new Promise((resolve) => {
      const counts = jatos.batchSession.get('stimulusConfigCounts') || { 3: 0, 4: 0 };
      const config = counts[3] <= counts[4] ? 3 : 4;
      counts[config] += 1;
      jatos.batchSession.set('stimulusConfigCounts', counts).then(() => resolve(config));
    });
  }

  // Generates a random node→fractal assignment that satisfies the symmetry
  // constraints for the given config (3 or 4).
  //
  // Graph boundary cross-edges: B↔E and D↔G.
  // Both communities must have exactly 2S and 2A nodes.
  //   Config 3: connected boundary pairs (B,E) and (D,G) are the same type as each other.
  //   Config 4: connected boundary pairs are different types from each other.
  //
  // Returns { map, typeMap } where:
  //   map     — { A: 'fractal19_S.png', B: 'fractal5_A.png', ... }
  //   typeMap — { A: 'S', B: 'A', ... }
  function assignStimuli(stimulusConfig) {
    const sPool = shuffleArray([...CONFIG.stimuliS]);
    const aPool = shuffleArray([...CONFIG.stimuliA]);

    // Randomly pick B's symmetry type; D is the opposite (community 1 needs 1S, 1A boundary).
    const bIsS = Math.random() < 0.5;
    const typeMap = {};
    typeMap['B'] = bIsS ? 'S' : 'A';
    typeMap['D'] = bIsS ? 'A' : 'S';

    // Config 3: E matches B, G matches D.
    // Config 4: E is opposite of B, G is opposite of D.
    if (stimulusConfig === 3) {
      typeMap['E'] = typeMap['B'];
      typeMap['G'] = typeMap['D'];
    } else {
      typeMap['E'] = bIsS ? 'A' : 'S';
      typeMap['G'] = bIsS ? 'S' : 'A';
    }

    // NB nodes: each community needs 1S and 1A among its two NB nodes.
    // Community 1 NB: graph nodes A and C.
    const [aType, cType] = Math.random() < 0.5 ? ['S', 'A'] : ['A', 'S'];
    typeMap['A'] = aType;
    typeMap['C'] = cType;

    // Community 2 NB: graph nodes F and H.
    const [fType, hType] = Math.random() < 0.5 ? ['S', 'A'] : ['A', 'S'];
    typeMap['F'] = fType;
    typeMap['H'] = hType;

    // Assign specific fractal images: draw from the shuffled pools in node order.
    let sIdx = 0, aIdx = 0;
    const map = {};
    for (const node of CONFIG.nodes) {
      map[node] = typeMap[node] === 'S' ? sPool[sIdx++] : aPool[aIdx++];
    }

    return { map, typeMap };
  }

  // Fisher-Yates in-place shuffle. Returns the same array.
  function shuffleArray(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  // Random walk over an adjacency list.
  // Picks a random start node, then at each step picks uniformly from neighbours.
  // Returns array of node labels of the given length.
  function generateRandomWalk(adjacency, nodes, length) {
    const walk = [];
    let current = nodes[Math.floor(Math.random() * nodes.length)];
    for (let i = 0; i < length; i++) {
      walk.push(current);
      const neighbours = adjacency[current];
      current = neighbours[Math.floor(Math.random() * neighbours.length)];
    }
    return walk;
  }

  // Deterministic practice walk: cycles I→J→K→I→... for the given length.
  function generatePracticeWalk(length) {
    const nodes = CONFIG.practiceNodes;
    return Array.from({ length }, (_, i) => nodes[i % nodes.length]);
  }

  // Reads Prolific URL parameters appended to the study link.
  // Returns { pid, studyId, sessionId } — empty strings if not present.
  function getProlificParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      pid:       params.get('PROLIFIC_PID') || '',
      studyId:   params.get('STUDY_ID')     || '',
      sessionId: params.get('SESSION_ID')   || ''
    };
  }

  // Loads and parses the counterbalancing CSV via PapaParse.
  // Returns a Promise resolving to an array of row objects.
  function loadCounterbalancingTable() {
    return new Promise((resolve, reject) => {
      Papa.parse(CONFIG.counterbalancingTablePath, {
        download: true,
        header:   true,
        // Leave question_code as a string — codes like "2E1" are valid JS scientific
        // notation and would be silently coerced to numbers by dynamicTyping.
        dynamicTyping: (field) => field !== 'question_code',
        complete: (results) => resolve(results.data),
        error:    (err)     => reject(err)
      });
    });
  }

  // Returns the trial rows for a given block number,
  // with a questionCode field aliased from the question_code column.
  function getTrialsForBlock(table, block) {
    return table
      .filter(row => row.block === block)
      .map(row => ({ ...row, questionCode: row.question_code }));
  }

  // Loads and parses the 2AFC question candidates CSV via PapaParse.
  // Returns a Promise resolving to an array of row objects.
  function loadQuestionCandidates() {
    return new Promise((resolve, reject) => {
      Papa.parse(CONFIG.questionCandidatesPath, {
        download:      true,
        header:        true,
        dynamicTyping: true,
        complete: (results) => resolve(results.data),
        error:    (err)     => reject(err)
      });
    });
  }

  // Builds a lookup table mapping question codes (e.g. "3F1") to candidate rows.
  // Relies on the question_number column in the candidates CSV (v3+).
  function buildQuestionLookup(candidates) {
    const tagToCategory = {};
    for (const [cat, tag] of Object.entries(CONFIG.categoryToPairTag)) {
      tagToCategory[tag] = parseInt(cat, 10);
    }

    const lookup = {};

    for (const row of candidates) {
      const category = tagToCategory[row.comparison_pair_tag];
      if (!category) continue;
      const code = `${category}${row.base}${row.question_number}`;
      lookup[code] = row;
    }

    return lookup;
  }

  // ---------- Exclusion checks ----------
  // Returns true if the participant should be excluded based on their miss pattern
  // for the given phase. Checks consecutive misses across all blocks and miss rate
  // within the current block. Either check can be disabled by setting it to null
  // in CONFIG.exclusion. Pass checkExclusion: true from main-task only — not practice.
  function shouldExclude(jsPsych, trialTypeLabel, block) {
    const cfg = trialTypeLabel === 'learning'
      ? CONFIG.exclusion.learning
      : CONFIG.exclusion.test;
    if (!cfg) return false;

    const trials = jsPsych.data
      .get()
      .filter({ trial_type_label: trialTypeLabel })
      .values();

    // Consecutive miss check (most recent trials first).
    if (cfg.maxConsecutiveMisses !== null) {
      let streak = 0;
      for (let i = trials.length - 1; i >= 0; i--) {
        if (trials[i].response === null) {
          streak++;
          if (streak >= cfg.maxConsecutiveMisses) return true;
        } else {
          break;
        }
      }
    }

    // Miss rate within the current block — only evaluated once the full block is
    // complete, so a single early miss doesn't produce a misleading 100% rate.
    if (cfg.maxMissRatePerBlock !== null) {
      const expectedCount = trialTypeLabel === 'learning'
        ? CONFIG.walkLength
        : CONFIG.questionsPerBlock;
      const blockTrials = trials.filter(t => t.block === block);
      if (blockTrials.length >= expectedCount) {
        const rate = blockTrials.filter(t => t.response === null).length / blockTrials.length;
        if (rate > cfg.maxMissRatePerBlock) return true;
      }
    }

    return false;
  }

  // ---------- Audio feedback ----------
  // Single AudioContext shared across all phases (created on first use).
  let _audioCtx = null;

  function _getAudioCtx() {
    if (!_audioCtx) {
      _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return _audioCtx;
  }

  // Short, soft confirmation tone (660 Hz sine, 50 ms).
  function playKeyTone() {
    try {
      const ctx = _getAudioCtx();
      ctx.resume();
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type            = 'sine';
      osc.frequency.value = 660;
      gain.gain.setValueAtTime(0.07, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.05);
    } catch (e) {}
  }

  // Descending tone played on timeout (440 → 200 Hz over 200 ms).
  function playTimeoutTone() {
    try {
      const ctx = _getAudioCtx();
      ctx.resume();
      const osc  = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(200, ctx.currentTime + 0.2);
      gain.gain.setValueAtTime(0.07, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.2);
    } catch (e) {}
  }

  return {
    getStimulusPath,
    shuffleArray,
    generateRandomWalk,
    generatePracticeWalk,
    getProlificParams,
    assignStimulusConfig,
    assignStimuli,
    loadCounterbalancingTable,
    getTrialsForBlock,
    loadQuestionCandidates,
    buildQuestionLookup,
    playKeyTone,
    playTimeoutTone,
    shouldExclude
  };

})();
