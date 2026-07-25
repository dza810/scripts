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

  get searchForm() {
    return this.getAttribute("searchForm")
  }

  set searchForm(value) {
    this.setAttribute("searchForm", value)
  }

  getAgGridElement() {
    console.log(this.agGrid);
    return document.querySelector(this.agGrid)
  }

  getSearchFormElement() {
    return document.querySelector(this.searchForm)
  }

  connectedCallback() {
    this.#setup();
  }

  #setup() {
    this.addEventListener("click", async () => {
      console.log("click")
      const updateData = this.getAgGridElement().getUpdateData()
      await fetch(this.api + `?screenCd=${window.screenCd}`, {
        headers: { "Content-Type": "application/json" },
        method: "POST",
        body: JSON.stringify(updateData)
      })
      this.getSearchFormElement().search()
    })
  }
}

customElements.define('submit-button', SubmitButton, { extends: "button" });

