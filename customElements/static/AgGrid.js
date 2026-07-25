export class AgGridDiv extends HTMLDivElement {
  #agGridOptions = undefined
  #originalData = []
  #agGridApi = undefined;

  #safeEval(params, code) {
    const getField = (field) => {
      return params?.data[field]
    }
    const value = params.value;
    const result = Function("getField", "value", `"use strict";return (${code});`)(getField, value)
    return result;
  }

  #defaultColDef = {
    filter: true,
    editable: true,
    cellStyle: params => {
      if (params.value === undefined) {
        return;
      }
      const cellStyleCodeStyle = params.colDef?.cellStyleCodeStyle;
      const code = params.colDef?.cellStyleCode
      if (!code || !cellStyleCodeStyle) { return }
      const result = this.#safeEval(params, code)
      if (result) {
        return JSON.parse(cellStyleCodeStyle);
      }
      return
    },
    cellClassRules: {
      'update-color': params => {
        if (params.data.isUpdated) {
          params.data.isUpdated = true;
          const field = params.colDef.field;
          if (!field) {
            return false;
          }
          const oldValue = this.#originalData?.get(params.data.id)[field]
          if (oldValue !== params.value) {
            return true;
          }
        }
        return false;
      }
    },
    onCellValueChanged: (params) => {
      if (params.oldValue !== params.newValue) {
        params.data.isUpdated = true;
        params.api.refreshCells({
          force: true
        });
        params.api.redrawRows({ rowNodes: [params.node] });
      }
    }
  }

  connectedCallback() {
    this.#setupAgGrid();
  }

  async #fetchOption() {
    if (!this.#agGridOptions) {
      this.#agGridOptions = await fetch("/getColumns", { headers: { 'Content-Type': 'application/json' } })
        .then(r => r.json());
    }
    return this.#agGridOptions;
  }

  async #convertToAgGridColumnDefs(columnOptions) {
    const columnDefs = []
    for (const colOpt of columnOptions) {
      const colDef = { ...colOpt }
      colDef.headerName = colOpt.viewName
      columnDefs.push(colDef);
    }
    return columnDefs;
  }

  async #setupAgGrid() {
    this.#agGridOptions = await this.#fetchOption();
    const { columnOptions, rowStyles } = this.#agGridOptions;
    const gridOptions = {
      rowData: this.rowData,
      columnDefs: await this.#convertToAgGridColumnDefs(columnOptions),
      defaultColDef: this.#defaultColDef,
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
        },
        "autoCalc": {
          editable: false,
          valueFormatter: (params) => {
            const code = params.colDef.code ?? "";
            return this.#safeEval(params, code);
          },
        },
        "text": {
          cellDataType: "text"
        },
        "number": {
          cellDataType: "number"
        },
        "boolean": {
          cellDataType: "boolean"
        },
        "checkbox": {
          cellDataType: "boolean"
        },
        "date": {
          cellDataType: "date"
        }
      },
      getRowStyle: params => {
        const style = {}
        for (const rowStyle of rowStyles) {
          if (!rowStyle.code || !rowStyle.style) {
            continue;
          }
          const codeResult = this.#safeEval(params, rowStyle.code)
          if (codeResult) {
            const styleResult = JSON.parse(rowStyle.style)
            for (const [key, value] of Object.entries(styleResult)) {
              if (value) {
                style[key] = value;
              }
            }
          }
        }
        return style;
      },
    };
    this.#agGridApi = agGrid.createGrid(this, gridOptions);
  }

  setRowData(rowData) {
    const originalData = JSON.parse(JSON.stringify(rowData));
    this.#originalData = new Map();
    for (const d of originalData) {
      this.#originalData.set(d.id, d);
    }
    console.log(this.#originalData);
    this.#agGridApi.setGridOption('rowData', rowData);
  }

  getUpdateData() {
    const beforeList = []
    const afterList = []
    this.#agGridApi.forEachNode((node) => {
      const data = node.data;
      if (data.isUpdated) {
        beforeList.push(this.#originalData.get(data.id));
        afterList.push({ ...data, changeType: "update" });
      }
    });
    return { afterList, beforeList }
  }
}

customElements.define('ag-grid', AgGridDiv, { extends: "div" });
