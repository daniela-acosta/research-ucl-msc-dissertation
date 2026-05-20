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

  // Correct cover task response for each practice node.
  // Placeholder values — update when real practice stimuli are defined.
  // Must match the key values in coverTask.symmetric / coverTask.notSymmetric.
  practiceCorrectAnswers: {
    I: 'f', // symmetric
    J: 'j', // not symmetric
    K: 'f'  // symmetric
  },

  // Placeholder practice 2AFC trials — replace once practice stimuli and questions are designed.
  // Each object: { base, optionTop, optionBottom, correctOption ('top'|'bottom') }
  practiceTwoAFCTrials: [
    { base: 'I', optionLeft: 'J', optionRight: 'K', correctOption: 'left' },
    { base: 'J', optionLeft: 'K', optionRight: 'I', correctOption: 'left' },
    { base: 'K', optionLeft: 'I', optionRight: 'J', correctOption: 'left' }
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
    left:        'f',
    right:       'j',
    leftLabel:   'F — Left',
    rightLabel:  'J — Right'
  },

  // --- Stimuli ---
  // Update stimulusExtension if the final asset format differs.
  stimulusDir:       'assets',
  stimulusExtension: '.png',

  // --- 2AFC question lookup ---
  // Maps category number → comparison_pair_tag string in the candidates CSV.
  categoryToPairTag: {
    1: 'NB1WB__NB2XB',
    2: 'NB1WB__NB1WNB',
    3: 'NB1WNB__NB2XB',
    4: 'B1WNB__B2WB',
    5: 'B1WNB__B2XNB',
    6: 'B2WB__B2XNB',
    7: 'B1XB__B2WB',
    8: 'B1WNB__B1XB',
    9: 'B1XB__B2XNB'
  },

  // --- Data / counterbalancing ---
  counterbalancingTablePath: 'data/counterbalancing_table.csv',
  questionCandidatesPath:    'data/2afc_question_candidates_v2.csv',

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
