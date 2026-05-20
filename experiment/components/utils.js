// Shared utilities. Requires CONFIG to be loaded first.

const Utils = (function () {

  // Returns the asset path for a given node label.
  function getStimulusPath(node) {
    return `${CONFIG.stimulusDir}/stimulus_${node}${CONFIG.stimulusExtension}`;
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

  // Assigns participant to the least-filled group using the JATOS Batch Session.
  // Increments that group's counter atomically.
  // Returns a Promise that resolves with the assigned group number (1-indexed integer).
  function assignGroup() {
    return new Promise((resolve) => {
      const counts = jatos.batchSession.get('groupCounts') || { 1: 0, 2: 0, 3: 0, 4: 0 };
      const leastFilled = Object.keys(counts).reduce((a, b) =>
        counts[a] <= counts[b] ? a : b
      );
      const group = parseInt(leastFilled, 10);
      counts[group] += 1;
      jatos.batchSession.set('groupCounts', counts).then(() => resolve(group));
    });
  }

  // Loads and parses the counterbalancing CSV via PapaParse.
  // Returns a Promise resolving to an array of row objects.
  function loadCounterbalancingTable() {
    return new Promise((resolve, reject) => {
      Papa.parse(CONFIG.counterbalancingTablePath, {
        download:       true,
        header:         true,
        dynamicTyping:  true,
        complete: (results) => resolve(results.data),
        error:    (err)     => reject(err)
      });
    });
  }

  // Returns the trial rows for a given group and block number,
  // with a questionCode field added from the appropriate Group_N column.
  function getTrialsForBlock(table, group, block) {
    const groupKey = `Group_${group}`;
    return table
      .filter(row => row.block === block)
      .map(row => ({ ...row, questionCode: row[groupKey] }));
  }

  return {
    getStimulusPath,
    shuffleArray,
    generateRandomWalk,
    generatePracticeWalk,
    getProlificParams,
    assignGroup,
    loadCounterbalancingTable,
    getTrialsForBlock
  };

})();
