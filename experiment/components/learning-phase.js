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
    const { walk, jsPsych, block, timed, giveFeedback } = params;
    const timeline = [];

    walk.forEach(function (node, stepIndex) {
      // 1. Stimulus + cover task response
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus:
          '<div class="stimulus-container">' +
          '<img src="' +
          Utils.getStimulusPath(node) +
          '" class="stimulus-image" alt="stimulus">' +
          "</div>" +
          '<p class="key-prompt">' +
          "<strong>" +
          CONFIG.coverTask.symmetricLabel +
          "</strong>" +
          "&nbsp;&nbsp;&nbsp;" +
          "<strong>" +
          CONFIG.coverTask.notSymmetricLabel +
          "</strong>" +
          "</p>",
        choices: [CONFIG.coverTask.symmetric, CONFIG.coverTask.notSymmetric],
        trial_duration: timed ? CONFIG.stimulusDuration : null,
        response_ends_trial: !timed,
        data: {
          trial_type_label: "learning",
          block: block,
          step: stepIndex,
          node: node,
        },
        on_finish: function (data) {
          data.cover_response = data.response;
          data.cover_rt = data.rt;
        },
      });

      // 2. Feedback (practice only)
      if (giveFeedback) {
        if (!timed) {
          // Untimed practice: show correct / incorrect based on expected answer
          const correctAnswer = CONFIG.practiceCorrectAnswers[node];
          timeline.push({
            type: jsPsychHtmlKeyboardResponse,
            stimulus: function () {
              const last = jsPsych.data.get().last(1).values()[0];
              const isCorrect = last.response === correctAnswer;
              return isCorrect
                ? '<p class="feedback-correct">Correct!</p>'
                : '<p class="feedback-incorrect">Incorrect — try again!</p>';
            },
            choices: "NO_KEYS",
            trial_duration: 600,
          });
        } else {
          // Timed practice: warn only if no response was given within the time limit
          timeline.push({
            timeline: [
              {
                type: jsPsychHtmlKeyboardResponse,
                stimulus:
                  '<p class="feedback-incorrect">Too slow! Please respond before the image disappears.</p>',
                choices: "NO_KEYS",
                trial_duration: 800,
              },
            ],
            conditional_function: function () {
              const last = jsPsych.data.get().last(1).values()[0];
              return last.response === null;
            },
          });
        }
      }

      // 3. ISI — blank screen between steps
      timeline.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: "",
        choices: "NO_KEYS",
        trial_duration: CONFIG.interStimulusInterval,
        data: { trial_type_label: 'isi' }
      });
    });

    return timeline;
  }

  return { createTimeline };
})();
