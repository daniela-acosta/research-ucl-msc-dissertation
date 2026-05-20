// Test-phase (2AFC) module. Requires CONFIG and Utils to be loaded first.

const TestPhase = (function () {

  /**
   * Build jsPsych timeline nodes for one test-phase block.
   *
   * @param {object}   params
   * @param {object[]} params.trials       - Trial rows from Utils.getTrialsForBlock (or practice placeholder array).
   * @param {object}   params.jsPsych      - The jsPsych instance.
   * @param {number}   params.block        - Block number (1-indexed), for data recording.
   * @param {boolean}  params.giveFeedback - Show correctness feedback after each trial (practice only).
   * @param {number}   params.group        - Counterbalancing group, for data recording.
   * @returns {object[]} Array of jsPsych timeline nodes.
   */
  function createTimeline(params) {
    const { trials, jsPsych, block, giveFeedback, group } = params;
    const shuffled = Utils.shuffleArray([...trials]);
    const timeline = [];

    // TODO: implement per-trial loop over shuffled array.
    // Each trial should produce:
    //   1. Randomise top/bottom assignment for optionA and optionB.
    //   2. html-keyboard-response trial:
    //        - stimulus: top/bottom layout showing base node + two option nodes as <img> elements
    //        - choices: [CONFIG.twoAFC.top, CONFIG.twoAFC.bottom]
    //        - trial_duration: CONFIG.testMaxResponseTime
    //        - response_ends_trial: true
    //        - on_finish: derive response ('top'|'bottom'|null), rt, timed_out
    //          Record full trial data object (see CLAUDE.md Data Recording section)
    //          Save to jatos.resultData (main task) or discard (practice)
    //   3. If giveFeedback: brief feedback trial showing correct/incorrect

    return timeline;
  }

  return { createTimeline };

})();
