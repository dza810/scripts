import { FetchButton } from "/static/fetchButton.js"
import { runFetch } from "/static/index.js"

class SubmitButton extends FetchButton {
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
      const data = this.getAgGridElement().getUpdateData()
      if (data.type == 'error') {
        throw new Error(JSON.stringify(data.errorList));
      } else if (data.type == 'ok') {
        delete data.type
        await runFetch(this.api, {
          method: "POST",
          body: data
        })
        await this.getSearchFormElement().search()
      } else if (data.type == 'nothing') {
        console.log(data)
      }
    })
  }
}

customElements.define('submit-button', SubmitButton, { extends: "button" });

