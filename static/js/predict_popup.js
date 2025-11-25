// static/js/predict_popup.js
// Clean + corrected + algo removed

document.addEventListener('DOMContentLoaded', function () {

  const careerForm = document.getElementById('careerForm');
  const predictBtn = document.getElementById('predictBtn');
  const resultEl = document.getElementById('result');

  if (!careerForm) {
    console.warn('careerForm not found in DOM');
    return;
  }

  const rawVal = (id) => {
    const el = document.getElementById(id);
    return el ? (el.value || '').toString().trim() : '';
  };

  const numVal = (id) => {
    const v = rawVal(id);
    return v === '' ? NaN : Number(v);
  };

  // --- REQUIRED PERCENTAGE FIELDS (algo removed) ---
  const requiredIds = ['os','prog','se','net','elec','arch','math','comm'];

  careerForm.addEventListener('submit', async function (e) {
    e.preventDefault();

    try {
      const bad = [];

      // validate required percentage fields
      for (let id of requiredIds) {
        const v = rawVal(id);
        if (v === '') { bad.push(id); continue; }
        const n = Number(v);
        if (!isFinite(n) || n < 35 || n > 100) { bad.push(id); }
      }

      if (bad.length) {
        resultEl.innerHTML = `⚠ Please enter valid (35–100) values for: <b>${bad.join(', ')}</b>`;
        return;
      }

      // Hackathon limit
      const hack = Number(document.getElementById('hack')?.value || 0);
      if (hack > 9) {
        resultEl.innerHTML = `⚠ Hackathons must be 0–9`;
        return;
      }

      // disable button while predicting
      if (predictBtn) {
        predictBtn.disabled = true;
        predictBtn.textContent = 'Predicting...';
      }

      resultEl.textContent = 'Predicting...';

      // --- Correct payload (algo removed) ---
      const payload = {
        "Acedamic percentage in Operating Systems": numVal('os') || 0,
        "Percentage in Programming Concepts": numVal('prog') || 0,
        "Percentage in Software Engineering": numVal('se') || 0,
        "Percentage in Computer Networks": numVal('net') || 0,
        "Percentage in Electronics Subjects": numVal('elec') || 0,
        "Percentage in Computer Architecture": numVal('arch') || 0,
        "Percentage in Mathematics": numVal('math') || 0,
        "Percentage in Communication skills": numVal('comm') || 0,

        "Logical quotient rating": Number(document.getElementById('logic')?.value || 0),
        "hackathons": hack,
        "coding skills rating": Number(document.getElementById('code')?.value || 0),
        "public speaking points": Number(document.getElementById('speak')?.value || 0),

        "self-learning capability?": Number(document.getElementById('self')?.value || 0),
        "Extra-courses did": Number(document.getElementById('extra')?.value || 0),

        // multi-select = count (backend friendly)
        "certifications": document.getElementById('cert').selectedOptions.length,
        "workshops": document.getElementById('work').selectedOptions.length,
        "reading and writing skills": document.getElementById('read').selectedOptions.length,
        "interested career area": document.getElementById('career').selectedOptions.length,
        "Type of company want to settle in?": document.getElementById('company').selectedOptions.length,

        "worked in teams ever?": Number(document.getElementById('team')?.value || 0)
      };

      console.log("Payload:", payload);

      // --- SEND TO BACKEND ---
      const res = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const text = await res.text();
        resultEl.innerHTML = `⚠ Server error: ${res.status}<br>${text}`;
        return;
      }

      const json = await res.json();

      if (json.error) {
        resultEl.innerHTML = `⚠ Error: ${json.error}`;
      } else {
        resultEl.innerHTML =
          `🎯 Predicted Career Role: <b>${json.predicted_job_role}</b>` +
          (json.confidence ? ` (confidence ${Math.round(json.confidence * 100)}%)` : "");
      }

    } catch (err) {
      console.error(err);
      resultEl.innerHTML = "⚠ Unexpected error (check console)";
    } finally {
      if (predictBtn) {
        predictBtn.disabled = false;
        predictBtn.textContent = 'Predict Career';
      }
    }
  });

});
