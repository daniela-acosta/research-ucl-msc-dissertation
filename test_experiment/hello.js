jatos.onLoad(function () {
  const statusEl = document.getElementById("status");
  const button = document.getElementById("submit-btn");

  statusEl.textContent = "JATOS loaded successfully.";

  button.addEventListener("click", function () {
    const resultData = {
      message: "Hello from JATOS",
      timestamp: new Date().toISOString(),
      workerId: jatos.workerId,
      studyId: jatos.studyId,
      componentId: jatos.componentId,
    };

    statusEl.textContent = "Submitting data...";

    jatos.submitResultData(resultData, function () {
      statusEl.textContent = "Data submitted successfully.";
      jatos.startNextComponent();
    });
  });

  console.log("JATOS workerId:", jatos.workerId);
  console.log("JATOS studyId:", jatos.studyId);
  console.log("JATOS componentId:", jatos.componentId);
  console.log("JATOS version:", jatos.version);
});
