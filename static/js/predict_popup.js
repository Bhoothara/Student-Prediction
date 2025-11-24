// static/js/predict_popup.js
// Robust handler for the career form predict button
document.addEventListener('DOMContentLoaded', function () {
  const careerForm = document.getElementById('careerForm');
  const predictBtn = document.getElementById('predictBtn');
  const resultEl = document.getElementById('result');

  if (!careerForm) {
    console.warn('careerForm not found in DOM');
    return;
  }

  if (!predictBtn) {
    console.warn('predictBtn not found in DOM');
  }

  // helper
  const rawVal = (id) => {
    const el = document.getElementById(id);
    return el ? (el.value || '').toString().trim() : '';
  };
  const numVal = (id) => {
    const v = rawVal(id);
    return v === '' ? NaN : Number(v);
  };

  careerForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    try {
      // basic validation example (you can expand)
      const requiredIds = ['os','algo','prog','se','net','elec','arch','math','comm'];
      const bad = [];
      for (let id of requiredIds) {
        const v = rawVal(id);
        if (v === '') { bad.push(id); continue; }
        const n = Number(v);
        if (!isFinite(n) || n < 0 || n > 100) { bad.push(id); }
      }
      if (bad.length) {
        resultEl.innerHTML = Please enter valid (0–100) values for: ${bad.join(', ')};
        return;
      }

      if (predictBtn) { predictBtn.disabled = true; predictBtn.textContent = 'Predicting...'; }
      resultEl.textContent = 'Predicting...';

      const payload = {
        "Acedamic percentage in Operating Systems": numVal('os') || 0,
        "percentage in Algorithms": numVal('algo') || 0,
        "Percentage in Programming Concepts": numVal('prog') || 0,
        "Percentage in Software Engineering": numVal('se') || 0,
        "Percentage in Computer Networks": numVal('net') || 0,
        "Percentage in Electronics Subjects": numVal('elec') || 0,
        "Percentage in Computer Architecture": numVal('arch') || 0,
        "Percentage in Mathematics": numVal('math') || 0,
        "Percentage in Communication skills": numVal('comm') || 0,
        "Logical quotient rating": Number(document.getElementById('logic')?.value || 0),
        "hackathons": Number(document.getElementById('hack')?.value || 0),
        "coding skills rating": Number(document.getElementById('code')?.value || 0),
        "public speaking points": Number(document.getElementById('speak')?.value || 0),
        "self-learning capability?": Number(document.getElementById('self')?.value || 0),
        "Extra-courses did": Number(document.getElementById('extra')?.value || 0),
        "certifications": Number(document.getElementById('cert')?.value || 0),
        "workshops": Number(document.getElementById('work')?.value || 0),
        "reading and writing skills": Number(document.getElementById('read')?.value || 0),
        "interested career area": Number(document.getElementById('career')?.value || 0),
        "Type of company want to settle in?": Number(document.getElementById('company')?.value || 0),
        "worked in teams ever?": Number(document.getElementById('team')?.value || 0)
      };

      console.debug('Payload for /predict:', payload);

      const res = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      // Check network response
      if (!res.ok) {
        const text = await res.text();
        console.error('Predict fetch failed', res.status, text);
        resultEl.innerHTML = Server error: ${res.status}. See console for details.;
      } else {
        const json = await res.json();
        console.debug('Predict response:', json);
        if (json && json.predicted_job_role) {
          resultEl.innerHTML = `🎯 Predicted Career Role: <b>${json.predicted_job_role}</b>${json.confidence ? ` (confidence ${Math.round(json.confidence*100)}%)` : ''}`;
        } else if (json && json.error) {
          resultEl.innerHTML = ⚠ Error: ${json.error};
        } else {
          resultEl.innerHTML = '⚠ Unexpected server response.';
        }
      }
    } catch (err) {
      console.error('Prediction handler error:', err);
      resultEl.innerHTML = '⚠ Cannot connect to backend or unexpected error (see console).';
    } finally {
      if (predictBtn) { predictBtn.disabled = false; predictBtn.textContent = 'Predict Career'; }
    }
  });
});