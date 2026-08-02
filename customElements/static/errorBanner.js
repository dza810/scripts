export class ErrorBanner extends HTMLDivElement {
  constructor() {
    super();
  }

  connectedCallback() {
    this.textContent = "no error"
    window.addEventListener('error', (event) => {
      this.textContent = `error: ${event?.message}`
    })
    window.addEventListener('unhandledrejection', (event) => {
      this.textContent = `error(promise): ${event?.reason}`
    });
  }
}

customElements.define('error-banner', ErrorBanner, { extends: "div" });
