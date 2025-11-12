document.addEventListener("DOMContentLoaded", function () {
  const chipSelects = document.querySelectorAll(".chip-enabled");

  chipSelects.forEach(select => {
    // create wrapper div
    const wrapper = document.createElement("div");
    wrapper.classList.add("chip-select");

    // move select inside wrapper
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(select);

    function updateChips() {
      // remove old chips
      wrapper.querySelectorAll(".chip").forEach(c => c.remove());

      // build chips
      Array.from(select.selectedOptions).forEach(opt => {
        const chip = document.createElement("div");
        chip.classList.add("chip");
        chip.textContent = opt.textContent;

        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "×";
        closeBtn.onclick = () => {
          opt.selected = false;
          updateChips();
        };

        chip.appendChild(closeBtn);
        wrapper.insertBefore(chip, select);
      });
    }

    select.addEventListener("change", updateChips);
    updateChips();
  });
});
