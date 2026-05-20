// Mock jatos.js for local development.
// When running on the JATOS server, JATOS intercepts requests for jatos.js and
// serves its own real implementation — this file is used only when opening HTML
// files directly in a browser without a JATOS server.
//
// All JATOS API calls are logged to the browser console so behaviour can be verified.

(function () {
  if (typeof jatos !== 'undefined') return; // real jatos.js already loaded

  console.log('[jatos mock] Local development mode — JATOS API is simulated.');

  const _batchStore = {}; // in-memory batch session storage (resets on page reload)

  window.jatos = {

    // --- Metadata ---
    workerId:    'local-worker-001',
    studyId:     'local-study',
    componentId: 'local-component',
    version:     'mock',

    // --- Shared session data ---
    // Persists across components in a real study run; resets on reload locally.
    studySessionData: {},

    // --- Batch session ---
    // Shared across participants in production; in-memory only locally.
    batchSession: {
      get: function (key) {
        return _batchStore[key];
      },
      set: function (key, value) {
        _batchStore[key] = value;
        console.log('[jatos mock] batchSession.set:', key, JSON.stringify(value));
        return Promise.resolve();
      }
    },

    // --- Lifecycle ---
    onLoad: function (callback) {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', callback);
      } else {
        callback();
      }
    },

    startNextComponent: function () {
      console.log('[jatos mock] startNextComponent() — would navigate to next component in production.');
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

    // --- Result data ---
    submitResultData: function (data, onSuccess) {
      console.log('[jatos mock] submitResultData:', JSON.stringify(data, null, 2));
      if (onSuccess) onSuccess();
    },

    appendResultData: function (data, onSuccess) {
      console.log('[jatos mock] appendResultData:', JSON.stringify(data, null, 2));
      if (onSuccess) onSuccess();
    }

  };
})();
