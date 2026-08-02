import { setupLoadingDialog } from "/static/index.js"

export class FetchButton extends HTMLButtonElement {
  constructor() {
    super();
  }
  #wrapped = new WeakMap();
  #origOnclick = null;

  addEventListener(type, listener, options) {
    if (type === 'click' && typeof listener === 'function') {
      const wrapped = this.#makeWrapped(listener);
      this.#wrapped.set(listener, wrapped);
      super.addEventListener(type, wrapped, options);
      return;
    }
    super.addEventListener(type, listener, options);
  }

  removeEventListener(type, listener, options) {
    const wrapped = this.#wrapped.get(listener);
    super.removeEventListener(type, wrapped ?? listener, options);
  }

  get onclick() {
    return this.#origOnclick;
  }

  set onclick(fn) {
    this.#origOnclick = fn;
    try {
      super.onclick = typeof fn === 'function' ? this.#makeWrapped(fn) : null;
    } catch(e) {
      console.error(e);
    }
  }

  #makeWrapped(fn) {
    return async (event) => {
      try {
        this.#preProcess(event);
        await fn.call(this, event);
      } finally {
        this.#postProcess(event);
      }
    };
  }

  #preProcess(event) {
    this.disabled = true;
    setupLoadingDialog().showModal();
  }
  #postProcess(event) {
    this.disabled = false;
    setupLoadingDialog().close();
    try {
      document.querySelector("#loadingDialog")?.close();
    } catch(e) {
      console.error(e);
    }
  }
}

customElements.define('fetch-button', FetchButton, { extends: "button" });
