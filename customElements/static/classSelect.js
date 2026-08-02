export class ClassSelect extends HTMLSelectElement {
  #abortController = undefined;
  #isConnected = false;
  #previousCode = null;
  #previousFetch = null;

  constructor() {
    super();
  }

  static get observedAttributes() {
    return ['code', 'required'];
  }

  get code() {
    return this.getAttribute("code");
  }

  set code(value) {
    return this.setAttribute("code", value);
  }

  connectedCallback() {
    this.#isConnected = true;
    this.#loadOptions()
    this.disabled = true;
  }

  async #loadOptions() {
    const code = this.code;
    console.log('#loadOptions', code);
    if (!this.#isConnected) {
      return;
    }

    // 以前の実行をキャンセルする
    this.#abortController?.abort();

    this.innerHTML = "";
    if (!this.code) {
      console.log('#loadOptions stop:', code)
      return;
    }

    this.#abortController = new AbortController();
    const signal = this.#abortController.signal;

    const opts = await this.#fetchOptions({ signal });
    if (!this.required) {
      opts.unshift({})
    }

    const options = []
    for (const opt of opts) {
      const option = document.createElement("option")
      if (opt.value) {
        option.value = opt.value;
      }
      if (opt.name) {
        option.textContent = opt.name;
      }
      options.push(option);
    }
    this.append(...options);
    this.disabled = false
  }

  async #fetchOptions({ signal }) {
    if (this.#previousCode === this.code) {
      return this.#previousFetch;
    }
    this.#previousFetch = await runFetch(`/getClass?code=${this.code}`, { signal });
    this.#previousCode = this.code
    return this.#previousFetch;
  }

  attributeChangedCallback(name, oldValue, newValue) {
    console.log('attributeChangedCallback', name, oldValue, newValue);
    switch (name) {
      case "code":
      case "required":
        if (oldValue !== newValue) {
          this.#loadOptions();
        }
        break;
    }
  }
}

customElements.define('class-select', ClassSelect, { extends: "select" });
