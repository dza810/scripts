class SubmitButton extends HTMLButtonElement {
  constructor() {
    super()
  }

  get api() {
    return this.getAttribute("api")
  }

  set api(value) {
    this.setAttribute("api", value)
  }

  get agGrid() {
    return this.getAttribute("agGrid")
  }

  set agGrid(value) {
    this.setAttribute("agGrid", value);
  }

  getAgGridElement() {
    console.log(this.agGrid);
    return document.querySelector(this.agGrid)
  }

  connectedCallback() {
    this.#setup();
  }

  #setup() {
    this.addEventListener("click", async () => {
      console.log("click")
      const { beforeList, afterList } = this.getAgGridElement().getUpdateData()
      await fetch(this.api, {
        headers: { "Content-Type": "application/json" },
        method: "POST",
        body: JSON.stringify({ beforeList, afterList })
      })
    })
  }
}

customElements.define('submit-button', SubmitButton, { extends: "button" });

