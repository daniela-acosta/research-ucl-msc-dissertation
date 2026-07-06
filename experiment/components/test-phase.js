// Test-phase (2AFC) module. Requires CONFIG and Utils to be loaded first.

const TestPhase = (function () {

  /**
   * Build jsPsych timeline nodes for one test-phase block.
   *
   * @param {object}        params
   * @param {object[]}      params.trials       - Trial rows from Utils.getTrialsForBlock,
   *                                              or CONFIG.practiceTwoAFCTrials for practice.
   * @param {object}        params.jsPsych      - The jsPsych instance.
   * @param {number}        params.block        - Block number (1-indexed); use 0 for practice.
   * @param {boolean}       params.timed        - true = 3000 ms time limit; false = no limit.
   * @param {boolean}       params.giveFeedback - Show feedback after each trial (practice only).
   * @param {object|null}   params.lookup       - Question-code → candidate-row map from
   *                                              Utils.buildQuestionLookup. Pass null for practice.
   * @returns {object[]} Array of jsPsych timeline nodes.
   */
  function createTimeline(params) {
    const { trials, jsPsych, block, timed, giveFeedback, collectConfidence, checkExclusion = false, lookup, stimulusConfig = null } = params;
    const isPractice = !lookup;
    const shuffled   = Utils.shuffleArray([...trials]);
    const timeline   = [];

    shuffled.forEach(function (trialRow, trialIndex) {

      // --- Resolve base node and option nodes ---
      let baseNode, leftNode, rightNode, leftIsA,
          optionAPlausible, optionBPlausible,
          comparisonPairTag, comparisonType,
          questionCode, category, correctPosition, candidate;

      if (isPractice) {
        // Practice trials already have optionLeft/optionRight/correctOption.
        // Do NOT re-randomise — positions are pre-assigned so feedback is unambiguous.
        baseNode         = trialRow.base;
        leftNode         = trialRow.optionLeft;
        rightNode        = trialRow.optionRight;
        correctPosition  = trialRow.correctOption; // 'left' | 'right'
        leftIsA          = null;
        optionAPlausible = null;
        optionBPlausible = null;
        comparisonPairTag = null;
        comparisonType    = null;
        questionCode      = null;
        category          = null;
      } else {
        // Main task: look up the candidate row and randomise left/right.
        questionCode = trialRow.questionCode;
        category     = trialRow.category;
        candidate = lookup[questionCode];

        if (!candidate) {
          console.warn('TestPhase: no candidate found for question code', questionCode, '— trial skipped.');
          return;
        }

        baseNode  = candidate.base;
        leftIsA   = Math.random() < 0.5;
        leftNode  = leftIsA ? candidate.optionA_dest : candidate.optionB_dest;
        rightNode = leftIsA ? candidate.optionB_dest : candidate.optionA_dest;

        optionAPlausible  = candidate.optionA_plausible;
        optionBPlausible  = candidate.optionB_plausible;
        comparisonPairTag = candidate.comparison_pair_tag;
        comparisonType    = candidate.comparison_type;
        correctPosition   = null;
      }

      // --- Build stimulus HTML ---
      // Only the base image goes in the stimulus; option images live inside the buttons.
      const stimulusHtml =
        '<div class="twoafc-base">' +
          '<p class="key-prompt">Which image is more likely to come next?</p>' +
          '<img src="' + Utils.getStimulusPath(baseNode) + '" class="stimulus-image" alt="base stimulus">' +
        '</div>';

      // --- 2AFC trial ---
      // Uses button response so participants click the image directly.
      // response: 0 = left, 1 = right, null = timed out.
      const leftChoiceHtml =
        '<img src="' + Utils.getStimulusPath(leftNode) + '" class="stimulus-image" alt="left option">' +
        '<p class="key-prompt">Click to choose</p>';
      const rightChoiceHtml =
        '<img src="' + Utils.getStimulusPath(rightNode) + '" class="stimulus-image" alt="right option">' +
        '<p class="key-prompt">Click to choose</p>';

      timeline.push({
        type:           jsPsychHtmlButtonResponse,
        stimulus:       stimulusHtml,
        choices:        [leftChoiceHtml, rightChoiceHtml],
        button_html:    '<button class="twoafc-btn">%choice%</button>',
        trial_duration: timed ? CONFIG.testMaxResponseTime : null,
        data: {
          trial_type_label:   'test',
          block:              block,
          trial_index_in_block: trialIndex,
          question_code:      questionCode,
          question_number:    candidate ? candidate.question_number : null,
          category:           category,
          comparison_pair_tag: comparisonPairTag,
          comparison_type:    comparisonType,
          base_node:          baseNode,
          option_left:        leftNode,
          option_right:       rightNode,
          left_is_option_a:   leftIsA,
          option_a_plausible: optionAPlausible,
          option_b_plausible: optionBPlausible,
          correct_position_practice: correctPosition,
          stimulus_config:    stimulusConfig
        },
        on_finish: function (data) {
          data.timed_out = data.response === null;
          if (data.timed_out) {
            Utils.playTimeoutTone();
            data.chosen_position = null;
            data.chosen_node     = null;
            data.chose_option_a  = null;
          } else {
            Utils.playKeyTone();
            if (data.response === 0) {
              data.chosen_position = 'left';
              data.chosen_node     = data.option_left;
              data.chose_option_a  = data.left_is_option_a;
            } else {
              data.chosen_position = 'right';
              data.chosen_node     = data.option_right;
              data.chose_option_a  = !data.left_is_option_a;
            }
          }
          // Plausibility of the chosen option (main task only)
          if (data.chose_option_a !== null && data.left_is_option_a !== null) {
            data.chose_plausible = data.chose_option_a
              ? data.option_a_plausible
              : data.option_b_plausible;
          } else {
            data.chose_plausible = null;
          }
        }
      });

      // --- Confidence judgement (skipped if 2AFC timed out) ---
      if (collectConfidence) {
        timeline.push({
          timeline: [{
          type:             jsPsychHtmlSliderResponse,
          stimulus:         '<p class="key-prompt">How confident are you in your response?</p>',
          data: { trial_type_label: 'confidence' },
          min:              CONFIG.confidence.min,
          max:              CONFIG.confidence.max,
          start:            50,
          step:             1,
          labels:           CONFIG.confidence.labels,
          require_movement: CONFIG.confidence.requireMovement,
          trial_duration:   CONFIG.confidence.maxResponseTime,
          on_start: function (trial) {
            trial.start = Math.floor(Math.random() * (CONFIG.confidence.max - CONFIG.confidence.min + 1))
                          + CONFIG.confidence.min;
          },
          on_finish: function (data) {
            // Write confidence back into the preceding 2AFC trial's data row.
            const twoAFCTrial = jsPsych.data
              .get()
              .filter({ trial_type_label: 'test' })
              .last(1)
              .values()[0];
            if (twoAFCTrial) {
              twoAFCTrial.confidence_response  = data.response;
              twoAFCTrial.confidence_rt        = data.rt;
              twoAFCTrial.confidence_timed_out = data.response === null;
            }
          }
          }],
          conditional_function: function () {
            const last = jsPsych.data.get().filter({ trial_type_label: 'test' }).last(1).values()[0];
            return last && !last.timed_out;
          }
        });
      }

      // --- Warnings (main task only) ---
      if (checkExclusion) {
        const _warnBlock = block;

        // Consecutive-miss warning — fires one miss before exclusion.
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: '<div class="text-content"><p><strong>Please try to respond!</strong> You have missed several responses in a row. If you miss the next one, the study will end automatically.</p><p>Please make sure to click one of the images before the time runs out.</p></div>',
            choices:  ['OK, I will try']
          }],
          conditional_function: function () {
            return Utils.shouldWarnConsecutiveMisses(jsPsych, 'test');
          }
        });

        // Cumulative miss-rate warning — fires once per block when rate hits 40%.
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: '<div class="text-content"><p><strong>You are missing too many responses.</strong> A high proportion of your responses so far have been missed. If this continues, the study will end automatically.</p><p>Please make sure to click one of the images before the time runs out.</p></div>',
            choices:  ['OK, I will try']
          }],
          conditional_function: function () {
            return Utils.shouldWarnMissRate(jsPsych, 'test', _warnBlock);
          }
        });
      }

      // --- Exclusion check (main task only) ---
      if (checkExclusion) {
        const _block = block;
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: '<div class="text-content"><p>The study has ended because too many responses were missed.</p><p>Please <strong>return your submission on Prolific</strong> by clicking "Stop without completing" on the Prolific website.</p><p>If you have any questions, please contact the researcher.</p></div>',
            choices:  ['OK'],
            on_finish: function () {
              if (typeof jatos !== 'undefined') {
                jatos.abortStudy('Excluded: missed too many test-phase responses.');
              }
              jsPsych.endExperiment();
            }
          }],
          conditional_function: function () {
            return Utils.shouldExclude(jsPsych, 'test', _block);
          }
        });
      }

      // --- Combined feedback (practice only) ---
      // Reads both the 2AFC outcome and the confidence timing from the test trial
      // row (confidence_timed_out is written back by the confidence on_finish) and
      // produces a single sentence so the two pieces of information feel unified.
      if (giveFeedback) {
        const expectedPosition   = correctPosition;
        const _collectConfidence = collectConfidence;
        const _timed             = timed;
        timeline.push({
          timeline: [{
            type: jsPsychHtmlKeyboardResponse,
            stimulus: function () {
              const last = jsPsych.data
                .get()
                .filter({ trial_type_label: 'test' })
                .last(1)
                .values()[0];

              if (last.timed_out) {
                return '<p class="feedback-incorrect">Too slow — try to respond before the time runs out.</p>';
              }

              const correct   = last.chosen_position === expectedPosition;
              const confSlow  = _collectConfidence && last.confidence_timed_out;

              if (correct && !confSlow) {
                return _timed
                  ? '<p class="feedback-correct">Correct, and great timing on both!</p>'
                  : '<p class="feedback-correct">Correct!</p>';
              }
              if (correct && confSlow) {
                return '<p class="feedback-correct">Correct answer! Try to rate your confidence a little faster though.</p>';
              }
              if (!correct && !confSlow) {
                return '<p class="feedback-incorrect">Not quite — pay attention to which image tends to appear next.</p>';
              }
              // incorrect + confidence slow
              return '<p class="feedback-incorrect">Not quite — and try to rate your confidence a little faster too.</p>';
            },
            choices:        'NO_KEYS',
            trial_duration: CONFIG.practiceFeedbackDuration
          }]
        });
      }
    });

    return timeline;
  }

  return { createTimeline };

})();
