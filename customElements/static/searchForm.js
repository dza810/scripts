export class SearchForm extends HTMLFormElement {
  #columnOptions = undefined
  connectedCallback() {
    this.#setupSearchForm()
  }

  get agGrid() {
    return this.getAttribute("agGrid");
  }

  set agGrid(value) {
    return this.setAttribute("agGrid", value);
  }

  get #agGridElement() {
    return document.querySelector(this.agGrid);
  }

  async #fetchOption() {
    if (!this.#columnOptions) {
      this.#columnOptions = await fetch(`/getColumns?screenCd=${window.screenCd}`, { headers: { 'Content-Type': 'application/json' } }).then(r => r.json());
    }
    return this.#columnOptions.columnOptions;
  }

  async #setupSearchForm() {
    const options = await this.#fetchOption();
    const customElements = Array.from(this.children)
    let index = -1;
    for (const option of options) {
      index++;
      let elm;
      switch (option.type) {
        case "dropdown":
          elm = document.createElement("select", { is: "class-select" });
          elm.code = option.column_cd
          break;
        case "text":
          elm = document.createElement("input");
          break;
        case "number":
          elm = document.createElement("input");
          elm.type = "number";
          break;
        case "checkbox":
          elm = document.createElement("select");
          let opt
          if (!option.required) {
            opt = document.createElement("option");
            elm.append(opt);
          }
          opt = document.createElement("option");
          opt.textContent = "true のみ";
          opt.value = "true";
          elm.append(opt);
          opt = document.createElement("option");
          opt.textContent = "false のみ";
          opt.value = "false";
          elm.append(opt);
          break;
        case "date":
          elm = document.createElement("input");
          elm.type = "date";
          break;
        case "autoCalc":
          /* 自動計算は飛ばす */
          break;
        default:
          console.warn(option);
      }

      if (elm) {
        const div = document.createElement("div");
        elm.name = option.column_name ?? `index-${index}`
        elm.required = !!(option.required ?? false);
        const label = document.createElement("label")
        label.textContent = option.viewName ?? elm.name;
        div.append(label);
        div.append(elm);
        this.append(div)
      }
    }

    for (const elm of customElements) {
      this.append(elm);
    }

    const div = document.createElement("div")
    const elm = document.createElement("button")
    elm.id = "searchButton"
    elm.name = "action";
    elm.value = "search";
    elm.textContent = "検索";
    elm.addEventListener('click', (e) => {
      e.preventDefault();
      this.search(e);
    })
    div.append(elm);
    this.append(div)
  }

  async search() {
    const formData = new FormData(this, this.querySelector("#searchButton"));
    const params = {}
    const options = await this.#fetchOption()
    for (const [key, data] of formData) {
      if (data != "") {
        const opt = options.find(o => o.column_cd === key);
        if (!opt) {
          continue
        }
        switch (opt.type) {
          case "checkbox":
            if (data == "true") {
              params[key] = true;
            } else if (data == "false") {
              params[key] = false;
            }
            break
          default:
            params[key] = data
        }
      }
    }
    this.#search(params).then(result => {
      if (this.#agGridElement) {
        try {
          this.#agGridElement.setRowData(result)
        } catch (e) {
          throw e;
        }
      }
    });
  }

  async #search(params) {
    return await runFetch(`/search`, {
      method: "POST",
      body: { params }
    })
  }
}

customElements.define('search-form', SearchForm, { extends: "form" });

