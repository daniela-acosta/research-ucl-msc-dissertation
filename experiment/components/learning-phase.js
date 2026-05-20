// Learning-phase module. Requires CONFIG and Utils to be loaded first.

const LearningPhase = (function () {

  /**
   * Build jsPsych timeline nodes for one learning-phase block.
   *
   * @param {object}   params
   * @param {string[]} params.walk         - Ordered node labels for this block (from Utils.generateRandomWalk).
   * @param {object}   params.jsPsych      - The jsPsych instance.
   * @param {number}   params.block        - Block number (1-indexed), for data recording.
   * @param {boolean}  params.giveFeedback - Show cover-task correctness feedback (practice only).
   * @returns {object[]} Array of jsPsych timeline nodes.
   */
  function createTimeline(params) {
    const { walk, jsPsych, block, giveFeedback } = params;
    const timeline = [];

    // TODO: implement per-step loop over walk array.
    // Each step should produce:
    //   1. html-keyboard-response trial:
    //        - stimulus: <img> of Utils.getStimulusPath(node) + symmetry prompt
    //        - choices: [CONFIG.coverTask.symmetric, CONFIG.coverTask.notSymmetric]
    //        - trial_duration: CONFIG.stimulusDuration
    //        - response_ends_trial: false  (advance on duration, not keypress)
    //        - on_finish: record { block, step: i, node, cover_response, cover_rt }
    //          and save to jatos.resultData (main task) or discard (practice)
    //   2. If giveFeedback: brief feedback trial showing correct/incorrect
    //   3. html-keyboard-response ISI trial:
    //        - stimulus: '' (blank)
    //        - trial_duration: CONFIG.interStimulusInterval
    //        - choices: 'NO_KEYS'

    return timeline;
  }

  return { createTimeline };

})();
