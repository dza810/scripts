export class ErrorBanner extends HTMLDivElement {
  constructor() {
    super();
  }

  connectedCallback() {
    this.textContent = "no error"
    console.log(this)
    window.addEventListener('error', (event) => {
      this.textContent = `error: ${event?.message}`
      console.log(`error: ${event.message}`, event)
    })
    window.addEventListener('unhandledrejection', (event) => {
      this.textContent = `error(promise): ${event?.message}`
      console.log(`error(promise): ${event.message}`, event)
    });
  }
}

customElements.define('error-banner', ErrorBanner, { extends: "div" });
