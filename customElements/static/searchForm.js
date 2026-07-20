class SearchForm extends HTMLFormElement {
  #columnOptions = undefined
  #agGridApi = undefined;
  #classOptions = new Map();
  async #fetchOption() {
    if (!this.#columnOptions) {
      this.#columnOptions = await fetch("/getColumns", { headers: { 'Content-Type': 'application/json' } }).then(r => r.json());
    }
    return this.#columnOptions;
  }

  connectedCallback() {
    this.#setupSearchForm().then(async _ => {
      this.#setupAgGrid();
    });
  }

  get agGrid() {
    return this.getAttribute("agGrid");
  }

  set agGrid(value) {
    return this.setAttribute("agGrid", value);
  }

  defaultColDef = {
    filter: true,
    editable: true,
  }

  async #convertToAgGridColumnDefs(columnOptions) {
    const columnDefs = []
    for (const colOpt of columnOptions) {
      const colDef = {...colOpt}
      colDef.headerName = colOpt.viewName
      columnDefs.push(colDef);
    }
    return columnDefs;
  }

  async #setupAgGrid() {
    const gridOptions = {
      rowData: this.rowData,
      columnDefs: await this.#convertToAgGridColumnDefs(this.#columnOptions),
      defaultColDef: this.defaultColDef,
      columnTypes: {
        "dropdown": {
          cellEditor: 'agSelectCellEditor',
          cellEditorParams: (params) => { 
            return {
              values: params.colDef?.classes?.map(v => v.value)
            }
          },
          valueFormatter: (params) => {
            return params.colDef?.classes?.find(v => params.value == v.value)?.name;
          },
          valueParser: (params) => {
            return params.colDef?.classes?.find(v => params.newValue == v.name)?.value;
          }
        }
      }
    };
    const myGridElement = document.querySelector(this.agGrid);
    this.#agGridApi = agGrid.createGrid(myGridElement, gridOptions);
  }

  async #setupSearchForm() {
    const options = await this.#fetchOption();
    console.log(options)
    const customElements = Array.from(this.children)
    let index = -1;
    for (const option of options) {
      index++;
      let elm;
      switch (option.type) {
        case "dropdown":
          elm = document.createElement("select", { is: "class-select" });
          elm.code = option.code
          break;
        case "text":
          elm = document.createElement("input");
          break;
        case "number":
          elm = document.createElement("input");
          elm.type = "number";
          break;
        case "checkbox":
          elm = document.createElement("input");
          elm.type = "checkbox";
          break;
        case "date":
          elm = document.createElement("input");
          elm.type = "date";
          break;
        default:
          console.warn(option);
      }

      if (elm) {
        const div = document.createElement("div");
        elm.name = option.field ?? `index-${index}`
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
    elm.name = "action";
    elm.value = "search";
    elm.textContent = "検索";
    elm.addEventListener('click', (e) => this.#clickSearchButton(e));
    div.append(elm);
    this.append(div)
  }

  #clickSearchButton(e) {
    e.preventDefault();
    const formData = new FormData(this, e.target);
    const request = {}
    for (const [key, data] of formData) {
      if (data != "") {
        request[key] = data
      }
    }
    // console.log(request);
    this.#search(request).then(result => {
      if (this.#agGridApi) {
        this.#agGridApi.setGridOption('rowData', result)
      }
    });
  }

  async #search(request) {
    return await fetch("/search", { header: { "Content-Type": "application/json" } }).then(r => r.json())
  }
}

customElements.define('search-form', SearchForm, { extends: "form" });

