const searchFormInputClasses = new Map();

const registerSearchFormInput = (clazz) => {
  let name = clazz.name
  if (name.endsWith("Input")) {
    name = name.substring(0, name.indexOf("Input"))
  }
  searchFormInputClasses.set(name.toLowerCase(), clazz)
}

class SearchFormInput {
  option;
  constructor(option) {
    this.option = option
  }

  getName(additional_name) {
    if (additional_name) {
      return this.option.column_name + "::" + additional_name
    } else {
      return this.option.column_name
    }
  }

  getViewName() {
    return this.option.viewName ?? this.getName()
  }

  makeLabel() {
    const label = document.createElement("label")
    label.textContent = this.getViewName();
    return label;
  }

  makeInput() {
    return document.createElement("input");
  }

  setFormAttrsToInput(elm, additional_name) {
    elm.name = this.getName(additional_name)
    // ここに required が出てくるのは変?
    elm.required = !!(this.option.required ?? false);
  }

  shouldMakeInput() {
    return true;
  }

  make() {
    if (!this.shouldMakeInput()) {
      return
    }
    const div = document.createElement("div");
    div.append(this.makeLabel())
    if (this.option.condition_cd == "between") {
      let elm = this.makeInput()
      this.setFormAttrsToInput(elm, "from")
      div.append(elm)
      const span = document.createElement("span")
      span.textContent = "~"
      div.append(span)
      elm = this.makeInput()
      this.setFormAttrsToInput(elm, "to")
      div.append(elm)
    } else {
      const elm = this.makeInput()
      this.setFormAttrsToInput(elm)
      div.append(elm)
    }
    return div;
  }
}

registerSearchFormInput(
  class DropdownInput extends SearchFormInput {
    makeInput() {
      const elm = document.createElement("select", { is: "class-select" });
      elm.code = this.option.column_cd
      return elm;
    }
  })

registerSearchFormInput(
  class TextInput extends SearchFormInput {
    makeInput() {
      const elm = document.createElement("input");
      return elm;
    }
  })

registerSearchFormInput(
  class NumberInput extends SearchFormInput {
    makeInput() {
      const elm = document.createElement("input");
      elm.type = "number";
      return elm;
    }
  })

registerSearchFormInput(
  class CheckboxInput extends SearchFormInput {
    makeInput() {
      const elm = document.createElement("select");
      let opt
      if (!this.option.required) {
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
    }
  })

registerSearchFormInput(
  class DateInput extends SearchFormInput {
    makeInput() {
      const elm = document.createElement("input");
      elm.type = "date";
      return elm;
    }
  })

const searchFormInputFactory = (option) => {
  const clazz = searchFormInputClasses.get(option.type)
  console.log(option, clazz)
  return new clazz(option);
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
    const children = Array.from(this.children)
    for (const option of options) {
      const div = searchFormInputFactory(option).make();
      this.append(div);
    }

    for (const elm of children) {
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
        const keySplitted = key.split("::")
        if (keySplitted.length >= 2) {
          let paramsTmp = params;
          for (const keyPart of keySplitted.slice(0, -1)) {
            paramsTmp[keyPart] = paramsTmp[keyPart] ?? {}
            paramsTmp = paramsTmp[keyPart]
          }
          paramsTmp[keySplitted.at(-1)] = data
          delete params[key]
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

