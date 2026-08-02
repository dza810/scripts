const searchFormImputFactory = {
  "dropdown": (option) => {
    const elm = document.createElement("select", { is: "class-select" });
    elm.code = option.column_cd
    return elm;
  },
  "text": () => {
    const elm = document.createElement("input");
    return elm;
  },
  "number": () => {
    const elm = document.createElement("input");
    elm.type = "number";
    return elm;
  },
  "checkbox": (option) => {
    const elm = document.createElement("select");
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
    return elm;
  },
  "date": () => {
    const elm = document.createElement("input");
    elm.type = "date";
    return elm;
  }
}


export class SearchForm extends HTMLFormElement {
  #searchFormOptions = undefined
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
    if (!this.#searchFormOptions) {
      this.#searchFormOptions = await fetch(`/getSearchForms?screenCd=${window.screenCd}`, { headers: { 'Content-Type': 'application/json' } }).then(r => r.json());
    }
    return this.#searchFormOptions
  }

  async #setupSearchForm() {
    const options = await this.#fetchOption();
    const customElements = Array.from(this.children)
    for (const option of options) {
      let factory = searchFormImputFactory?.[option.type];
      if (!factory) {
        console.warn('invalid option', option);
        continue
      }
      const elm = factory(option)
      if (elm) {
        const div = document.createElement("div");
        elm.name = option.search_form_cd
        const label = document.createElement("label")
        label.textContent = `(${option.condition_cd})${option.search_form_name ?? elm.name}`;
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
    elm.textContent = "検索";
    elm.addEventListener('click', async (e) => {
      e.preventDefault();
      await this.search(e);
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
        const opt = options.find(o => o.column_cd === key) ?? {};
        switch (opt?.type) {
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

