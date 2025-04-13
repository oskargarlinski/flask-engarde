function updateValueDropdown(groupName) {
    const entries = document.querySelectorAll(`[name^="${groupName}-"]`);

    entries.forEach((_, index) => {
        const optionSelect = document.querySelector(`[name="${groupName}-${index}-option_name"]`);
        const valueSelect = document.querySelector(`[name="${groupName}-${index}-option_value"]`);
        const hiddenInput = document.querySelector(`[name="${groupName}-${index}-${groupName === 'pricing_rules' ? 'match_conditions' : 'value_name'}"]`);

        if (optionSelect && valueSelect) {
            const refreshValues = () => {
                const selectedOption = optionSelect.value;
                const values = optionValueMap[selectedOption] || [];

                valueSelect.innerHTML = "";
                values.forEach(val => {
                    const opt = document.createElement("option");
                    opt.value = val;
                    opt.textContent = val;
                    valueSelect.appendChild(opt);
                });

                if (hiddenInput) {
                    hiddenInput.value = `${optionSelect.value}=${valueSelect.value}`;
                }
            };

            optionSelect.addEventListener("change", refreshValues);
            valueSelect.addEventListener("change", () => {
                if (hiddenInput) {
                    hiddenInput.value = `${optionSelect.value}=${valueSelect.value}`;
                }
            });

            refreshValues();
        }
    });
}

function addRule() {
    const container = document.getElementById("rules-container");
    const count = container.querySelectorAll('.rule-entry').length;
    const options = Object.keys(optionValueMap);
    const defaultOption = options[0];
    const values = optionValueMap[defaultOption] || [];

    const html = `
      <div class="card mb-2 p-3 bg-light border rule-entry">
        <div class="d-flex justify-content-between align-items-start">
          <strong>Rule ${count + 1}</strong>
          <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.rule-entry').remove()">Delete</button>
        </div>
        <div class="row mt-2">
          <div class="col-md-3 mb-2">
            <label class="form-label">Option</label>
            <select name="pricing_rules-${count}-option_name" class="form-select">
              ${options.map(o => `<option value="${o}">${o}</option>`).join("")}
            </select>
          </div>
          <div class="col-md-3 mb-2">
            <label class="form-label">Value</label>
            <select name="pricing_rules-${count}-option_value" class="form-select">
              ${values.map(v => `<option value="${v}">${v}</option>`).join("")}
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">Price</label>
            <input class="form-control" name="pricing_rules-${count}-base_price" type="number" step="0.01" />
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">Impact</label>
            <input class="form-control" name="pricing_rules-${count}-base_impact" type="number" step="0.01" />
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">Stock</label>
            <input class="form-control" name="pricing_rules-${count}-stock" type="number" />
          </div>
        </div>
        <input type="hidden" name="pricing_rules-${count}-match_conditions" />
      </div>
    `;
    container.insertAdjacentHTML("beforeend", html);
    updateValueDropdown("pricing_rules");
}

function addModifier() {
    const container = document.getElementById("modifiers-container");
    const count = container.querySelectorAll('.modifier-entry').length;
    const options = Object.keys(optionValueMap);
    const defaultOption = options[0];
    const values = optionValueMap[defaultOption] || [];

    const html = `
      <div class="card mb-2 p-3 bg-white border modifier-entry">
        <div class="d-flex justify-content-between align-items-start">
          <strong>Modifier ${count + 1}</strong>
          <button type="button" class="btn btn-sm btn-danger" onclick="this.closest('.modifier-entry').remove()">Delete</button>
        </div>
        <div class="row mt-2">
          <div class="col-md-3 mb-2">
            <label class="form-label">Option</label>
            <select name="modifiers-${count}-option_name" class="form-select">
              ${options.map(o => `<option value="${o}">${o}</option>`).join("")}
            </select>
          </div>
          <div class="col-md-3 mb-2">
            <label class="form-label">Value</label>
            <select name="modifiers-${count}-option_value" class="form-select">
              ${values.map(v => `<option value="${v}">${v}</option>`).join("")}
            </select>
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">+£</label>
            <input class="form-control" name="modifiers-${count}-price_modifier" type="number" step="0.01" />
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">+kg CO₂</label>
            <input class="form-control" name="modifiers-${count}-impact_modifier" type="number" step="0.01" />
          </div>
          <div class="col-md-2 mb-2">
            <label class="form-label">+ Stock</label>
            <input class="form-control" name="modifiers-${count}-stock_modifier" type="number" />
          </div>
        </div>
        <input type="hidden" name="modifiers-${count}-value_name" />
      </div>
    `;
    container.insertAdjacentHTML("beforeend", html);
    updateValueDropdown("modifiers");
}


document.addEventListener("DOMContentLoaded", function () {
    updateValueDropdown("pricing_rules");
    updateValueDropdown("modifiers");
});
