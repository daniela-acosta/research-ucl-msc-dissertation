// Mock jatos.js for local development.
// When running on the JATOS server, JATOS intercepts requests for jatos.js and
// serves its own real implementation — this file is used only when opening HTML
// files directly in a browser without a JATOS server.

(function () {
  if (typeof jatos !== 'undefined') return;

  console.log('[jatos mock] Local development mode — JATOS API is simulated.');

  window.jatos = {

    workerId:    'local-worker-001',
    studyId:     'local-study',
    componentId: 'local-component',
    version:     'mock',

    studySessionData: {},

    batchSession: {
      _store: {},
      get: function (key) { return this._store[key]; },
      set: function (key, value) {
        this._store[key] = value;
        console.log('[jatos mock] batchSession.set:', key, JSON.stringify(value));
        return Promise.resolve();
      }
    },

    onLoad: function (callback) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback);
      } else {
        callback();
      }
    },

    startNextComponent: function () {
      console.log('[jatos mock] startNextComponent() — would navigate to next component.');
    },

    endStudy: function (successful) {
      console.log('[jatos mock] endStudy(' + successful + ') — study ended.');
      document.body.innerHTML =
        '<div style="padding:60px;font-family:sans-serif;color:#333;text-align:center;">' +
        '<h2>Study complete</h2><p>Thank you! (Local dev mode — data logged to console.)</p></div>';
    },

    endStudyAndRedirect: function (url) {
      console.log('[jatos mock] endStudyAndRedirect() → ' + url);
    },

    abortStudy: function (message) {
      console.warn('[jatos mock] abortStudy(): ' + message);
      document.body.innerHTML =
        '<div style="padding:40px;font-family:sans-serif;color:#333;">' +
        '<h2>Study ended</h2><p>' + message + '</p></div>';
    },

    submitResultData: function (data, onSuccess) {
      console.log('[jatos mock] submitResultData:', JSON.parse(data));
      if (onSuccess) onSuccess();
    },

    appendResultData: function (data, onSuccess) {
      console.log('[jatos mock] appendResultData:', JSON.parse(data));
      if (onSuccess) onSuccess();
    }

  };
})();
