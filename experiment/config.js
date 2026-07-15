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
    E: ['B', 'F', 'H'],
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

  // Stimulus files for practice nodes I, J, K — paths relative to stimulusDir.
  practiceStimuli: {
    I: 'practice/asymmetrical/fractal9_A.png',   // asymmetrical
    J: 'practice/symmetrical/fractal2_S.png',    // symmetrical
    K: 'practice/symmetrical/fractal22_S.png'    // symmetrical
  },

  // Correct cover task response for each practice node.
  // Must match the key values in coverTask.symmetric / coverTask.notSymmetric.
  practiceCorrectAnswers: {
    I: 'j', // fractal9_A  — asymmetrical
    J: 'f', // fractal2_S  — symmetrical
    K: 'f'  // fractal22_S — symmetrical
  },

  // Placeholder practice 2AFC trials — replace once practice stimuli and questions are designed.
  // Each object: { base, optionLeft, optionRight, correctOption ('left'|'right') }
  practiceTwoAFCTrials: [
    { base: 'I', optionLeft: 'J', optionRight: 'K', correctOption: 'left' },
    { base: 'J', optionLeft: 'K', optionRight: 'I', correctOption: 'left' },
    { base: 'K', optionLeft: 'I', optionRight: 'J', correctOption: 'left' }
  ],

  // --- Timing (ms) ---
  stimulusDuration:       2000,
  interStimulusInterval:  200,
  testMaxResponseTime:    4000,
  learningToTestPause:    2000,  // blank-ish pause between learning and test phases

  // --- Block structure ---
  numBlocks:         4,
  questionsPerBlock: 36,
  walkLength:        48,

  // Limit test-phase questions per block for fast testing. Set to null for full run.
  testQuestionsLimit: null,

  // --- Breaks ---
  breakDuration: 180,   // seconds; max rest time between blocks before auto-advance

  // --- Practice ---
  practiceFeedbackDuration:  2500, // ms; how long feedback is shown after each practice trial
  practiceWalkLength:        5,
  practiceQuestionsPerBlock: 3,   // placeholder — update when practice questions are defined

  // --- Confidence judgement ---
  // Shown after every 2AFC trial. Slider from min to max with a randomised start.
  // require_movement forces participants to actively move the slider before submitting.
  confidence: {
    min:             0,
    max:             100,
    labels:          ['Totally guessing', 'Completely confident'],
    requireMovement: true,
    maxResponseTime: 5000
  },

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
  stimulusDir:       'assets',
  stimulusExtension: '.png',

  // The 8 selected fractal images split by symmetry type.
  // assignStimuli() draws from these pools when building the node→image map.
  stimuliS: ['fractal19_S.png', 'fractal9_S.png', 'fractal20_S.png', 'fractal10_S.png'],
  stimuliA: ['fractal5_A.png',  'fractal15_A.png', 'fractal4_A.png',  'fractal6_A.png'],

  // --- 2AFC question lookup ---
  // Maps category number → comparison_pair_tag string in the candidates CSV.
  categoryToPairTag: {
    1: 'NB1WB__NB2XB',
    2: 'NB1WNB__NB2XB',
    3: 'NB1WB__NB1WNB',
    4: 'B2WB__B2XNB',
    5: 'B1WNB__B2WB',
    6: 'B1WNB__B2XNB',
    7: 'B1XB__B2WB',
    8: 'B1XB__B2XNB',
    9: 'B1WNB__B1XB',
  },

  // --- Random walk validation ---
  // Walks that fail any criterion are discarded and regenerated at study start.
  walkValidation: {
    minNodeAppearances:   3,
    maxCommunityFraction: 2/3,
    maxNodeFraction:      1/5,
  },

  // --- Data / counterbalancing ---
  counterbalancingTablePath: 'data/counterbalancing_table_v2.csv',
  questionCandidatesPath:    'data/2afc_question_candidates_v3.csv',

  // --- Prolific ---
  // Three distinct completion paths — each maps to a different Prolific action.
  prolificCompletionURL:    'https://app.prolific.com/submissions/complete?cc=C104P3H9',  // full completion → standard reward
  prolificScreenOutURL:     'https://app.prolific.com/submissions/complete?cc=C11G0DN3',  // comprehension fail → screen-out reward
  prolificAttentionExitURL: 'https://app.prolific.com/submissions/complete?cc=C10213M3', // attention fail → awaiting review

  // Completion codes shown on end screens and embedded in redirect URLs.
  completionCodes: {
    complete:               'C104P3H9',
    screenOutComprehension: 'C11G0DN3',
    earlyExitAttention:     'C10213M3',
  },

  // Secret PID value that bypasses the missing-PID check and skips the Prolific
  // completion redirect at the end. Use ?PROLIFIC_PID=PREVIEW in the URL to test.
  previewPID: 'PREVIEW',

  // --- Exclusion criteria ---
  // Participants are excluded (study aborted) if either criterion is met during the
  // main task. Set a value to null to disable that check for the relevant phase.
  // maxConsecutiveMisses: N unanswered trials in a row (checked after every trial).
  // maxMissRatePerBlock:  proportion of missed trials in the current block (0–1).
  exclusion: {
    learning: {
      maxConsecutiveMisses: 3,
      maxMissRatePerBlock:  0.25   // exclude at end of block if ≥ 25% missed; warning fires 1 miss before
    },
    test: {
      maxConsecutiveMisses: 3,
      maxMissRatePerBlock:  0.25
    }
  },

  // --- JATOS studySessionData keys ---
  sessionKeys: {
    prolificPID:     'prolific_pid',
    studyID:         'study_id',
    sessionID:       'session_id',
    walkSequences:   'walk_sequences',
    stimulusConfig:  'stimulus_config',   // 3 or 4
    stimulusMap:     'stimulus_map',      // { A: 'fractal19_S.png', B: ..., ... }
    stimulusTypeMap: 'stimulus_type_map'  // { A: 'S', B: 'A', ... }
  }

};
