// Central configuration for the Graph Learning Experiment.
// All tunable parameters live here — do not scatter values through component files.

const CONFIG = {

  // --- Graph ---
  nodes: ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
  boundaryNodes:    ['B', 'D', 'E', 'G'],
  nonBoundaryNodes: ['A', 'C', 'F', 'H'],
  communities: {
    1: ['A', 'B', 'C', 'D'],
    2: ['E', 'F', 'G', 'H']
  },
  adjacency: {
    A: ['B', 'C', 'D'],
    B: ['A', 'C', 'E'],
    C: ['A', 'B', 'D'],
    D: ['A', 'C', 'G'],
    E: ['B', 'F', 'G'],
    F: ['E', 'G', 'H'],
    G: ['D', 'F', 'H'],
    H: ['E', 'F', 'G']
  },

  // --- Practice graph ---
  // One neighbour per node forces a deterministic I→J→K→I→... walk.
  practiceNodes: ['I', 'J', 'K'],
  practiceAdjacency: {
    I: ['J'],
    J: ['K'],
    K: ['I']
  },

  // Placeholder practice 2AFC trials — replace once practice stimuli and questions are designed.
  // Each object: { base, optionTop, optionBottom, correctOption ('top'|'bottom') }
  practiceTwoAFCTrials: [
    { base: 'I', optionTop: 'J', optionBottom: 'K', correctOption: 'top' },
    { base: 'J', optionTop: 'K', optionBottom: 'I', correctOption: 'top' },
    { base: 'K', optionTop: 'I', optionBottom: 'J', correctOption: 'top' }
  ],

  // --- Timing (ms) ---
  stimulusDuration:      2000,
  interStimulusInterval: 200,
  testMaxResponseTime:   3000,

  // --- Block structure ---
  numBlocks:         4,
  questionsPerBlock: 9,
  walkLength:        26,

  // --- Practice ---
  practiceWalkLength:        26,  // same as main task; adjust here to change
  practiceQuestionsPerBlock: 3,   // placeholder — update when practice questions are defined

  // --- Response keys ---
  coverTask: {
    symmetric:         'f',
    notSymmetric:      'j',
    symmetricLabel:    'F — Symmetric',
    notSymmetricLabel: 'J — Not symmetric'
  },
  twoAFC: {
    top:         'f',
    bottom:      'j',
    topLabel:    'F — Top',
    bottomLabel: 'J — Bottom'
  },

  // --- Stimuli ---
  // Update stimulusExtension if the final asset format differs.
  stimulusDir:       'assets',
  stimulusExtension: '.png',

  // --- Data / counterbalancing ---
  counterbalancingTablePath: '../data/counterbalancing_table.csv',

  // --- Prolific ---
  prolificCompletionURL: 'PLACEHOLDER_COMPLETION_URL',

  // --- JATOS studySessionData keys ---
  sessionKeys: {
    group:         'group',
    prolificPID:   'prolific_pid',
    studyID:       'study_id',
    sessionID:     'session_id',
    walkSequences: 'walk_sequences'
  }

};
