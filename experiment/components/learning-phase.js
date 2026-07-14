// Learning-phase module. Requires CONFIG and Utils to be loaded first.

const LearningPhase = (function () {

  /**
   * Build jsPsych timeline nodes for one learning-phase block.
   *
   * @param {object}   params
   * @param {string[]} params.walk         - Ordered node labels (from Utils.generateRandomWalk or generatePracticeWalk).
   * @param {object}   params.jsPsych      - The jsPsych instance.
   * @param {number}   params.block        - Block number (1-indexed); use 0 for practice.
   * @param {boolean}  params.timed        - true  = fixed stimulus duration, record response in window (main task & timed practice).
   *                                         false = wait indefinitely for response (untimed practice).
   * @param {boolean}  params.giveFeedback - Show feedback after each step (practice only).
   *                                         Untimed: shows correct / incorrect.
   *                                         Timed:   shows timeout warning only if no response was given.
   * @returns {object[]} Array of jsPsych timeline nodes.
   */
  function createTimeline(params) {
    const { walk, jsPsych, block, timed, giveFeedback, checkExclusion = false, stimulusConfig = null } = params;
    const timeline = [];

    walk.forEach(function (node, stepIndex) {
      let _keyHandler = null;

      // 1. Stimulus + cover task response
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus:
          '<div class="stimulus-container">' +
            '<img src="' + Utils.getStimulusPath(node) + '" class="stimulus-image" alt="stimulus">' +
          '</div>' +
          '<p class="key-prompt">' +
            '<strong id="cover-label-sym">'    + CONFIG.coverTask.symmetricLabel    + '</strong>' +
            '&nbsp;&nbsp;&nbsp;' +
            '<strong id="cover-label-notsym">' + CONFIG.coverTask.notSymmetricLabel + '</strong>' +
          '</p>',
        choices: [CONFIG.coverTask.symmetric, CONFIG.coverTask.notSymmetric],
        trial_duration:      timed ? CONFIG.stimulusDuration : null,
        response_ends_trial: !timed,
        data: {
          trial_type_label: 'learning',
          block:            block,
          step:             stepIndex,
          node:             node,
          stimulus_config:  stimulusConfig,
        },
        on_load: function () {
          _keyHandler = function (e) {
            if (e.key === CONFIG.coverTask.symmetric || e.key === CONFIG.coverTask.notSymmetric) {
              Utils.playKeyTone();
              // Highlight the pressed label; dim the other
              const pressedId = e.key === CONFIG.coverTask.symmetric ? 'cover-label-sym' : 'cover-label-notsym';
              const otherId   = e.key === CONFIG.coverTask.symmetric ? 'cover-label-notsym' : 'cover-label-sym';
              const pressed   = document.getElementById(pressedId);
              const other     = document.getElementById(otherId);
              if (pressed) pressed.style.color = '#2980b9';
              if (other)   other.style.color   = '#aaaaaa';
              document.removeEventListener('keydown', _keyHandler);
              _keyHandler = null;
            }
          };
          document.addEventListener('keydown', _keyHandler);
        },
        on_finish: function (data) {
          if (_keyHandler) {
            document.removeEventListener('keydown', _keyHandler);
            _keyHandler = null;
          }
          data.cover_response = data.response;
          data.cover_rt       = data.rt;
        },
      });

      // 2. Feedback (practice only)
      if (giveFeedback) {
        if (!timed) {
          const correctAnswer = CONFIG.practiceCorrectAnswers[node];
          timeline.push({
            type: jsPsychHtmlKeyboardResponse,
            stimulus: function () {
              const last = jsPsych.data.get().last(1).values()[0];
              return last.response === correctAnswer
                ? '<p class="feedback-correct">Correct!</p>'
                : '<p class="feedback-incorrect">Incorrect — try again!</p>';
            },
            choices:        'NO_KEYS',
            trial_duration: CONFIG.practiceFeedbackDuration,
          });
        } else {
          timeline.push({
            timeline: [{
              type:           jsPsychHtmlKeyboardResponse,
              stimulus:       '<p class="feedback-incorrect">Too slow! Please respond before the image disappears.</p>',
              choices:        'NO_KEYS',
              trial_duration: CONFIG.practiceFeedbackDuration,
            }],
            conditional_function: function () {
              return jsPsych.data.get().last(1).values()[0].response === null;
            },
          });
        }
      }

      // 3. ISI — blank screen between steps
      timeline.push({
        type:           jsPsychHtmlKeyboardResponse,
        stimulus:       '',
        choices:        'NO_KEYS',
        trial_duration: CONFIG.interStimulusInterval,
        data:           { trial_type_label: 'isi' }
      });

      // 4. Warnings (main task only)
      if (checkExclusion) {
        const _warnBlock = block;

        // Consecutive-miss warning — fires one miss before exclusion.
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: '<div class="text-content"><p><strong>Please try to respond!</strong> You have missed several responses in a row. If you miss the next one, the study will end automatically.</p><p>Please make sure to press <strong>F</strong> or <strong>J</strong> before each image disappears.</p></div>',
            choices:  ['OK, I will try']
          }],
          conditional_function: function () {
            return Utils.shouldWarnConsecutiveMisses(jsPsych, 'learning');
          }
        });

        // Cumulative miss-rate warning — fires once per block when rate hits 40%.
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: '<div class="text-content"><p><strong>You are missing too many responses.</strong> A high proportion of your responses so far have been missed. If this continues, the study will end automatically.</p><p>Please make sure to press <strong>F</strong> or <strong>J</strong> before each image disappears.</p></div>',
            choices:  ['OK, I will try']
          }],
          conditional_function: function () {
            return Utils.shouldWarnMissRate(jsPsych, 'learning', _warnBlock);
          }
        });
      }

      // 5. Exclusion check (main task only)
      if (checkExclusion) {
        const _block = block;
        timeline.push({
          timeline: [{
            type:     jsPsychHtmlButtonResponse,
            stimulus: `
              <div class="text-content">
                <p>The study has ended because too many responses were missed.</p>
                <p>Your completion code is:<br>
                   <strong style="font-size:1.3em;letter-spacing:2px;">${CONFIG.completionCodes.earlyExitAttention}</strong></p>
                <p>You will be redirected to Prolific automatically. If not, please return to
                   Prolific and enter the code above.</p>
                <p>If you have any questions, please contact the researcher.</p>
              </div>`,
            choices:  ['OK'],
            on_finish: function () {
              jatos.studySessionData.earlyExit = true;
              jatos.submitResultData(JSON.stringify({
                exit_type:  'attention_fail',
                exit_phase: 'learning',
                exit_block: _block,
              }));
              Utils.endStudyRoute(CONFIG.prolificAttentionExitURL);
              jsPsych.endExperiment();
            }
          }],
          conditional_function: function () {
            return Utils.shouldExclude(jsPsych, 'learning', _block);
          }
        });
      }
    });

    return timeline;
  }

  return { createTimeline };
})();
