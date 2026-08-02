import { runFetch } from "/static/index.js"

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
    editable: (params) => params.data.__isInserted || !!params.colDef.isEditable,
    cellStyle: params => {
      if (params.value === undefined) {
        return;
      }
      const cellStyleCodeStyle = params.colDef?.cell_style_code_style;
      const code = params.colDef?.cell_style_code_condition;
      if (!code || !cellStyleCodeStyle) { return }
      const result = this.#safeEval(params, code)
      if (result) {
        const style = JSON.parse(cellStyleCodeStyle);
        console.debug('enabled', code, style)
        return style
      }
      return
    },
    cellClassRules: {
      'update-color': params => {
        if (!params.data.__isDeleted && params.data.__isUpdated) {
          const field = params.colDef.field;
          if (!field) {
            return false;
          }
          const oldValue = this.#originalData?.get(params.data.id)?.[field]
          if (oldValue !== params.value) {
            return true;
          }
        }
        return false;
      },
      'delete-color': params => {
        return params.data.__isDeleted;
      },
      'error-color': params => {
        return params.data?.__error?.[params.colDef.field]
      },
      'uneditable-color': params => {
        return !params.colDef.editable(params);
      }
    },
    onCellValueChanged: (params) => {
      if (params.oldValue !== params.newValue) {
        params.data.__isUpdated = true;
        params.api.refreshCells({
          force: true
        });
        params.api.redrawRows({ rowNodes: [params.node] });
      }
    },
    valueSetter: (params) => {
      this.#clearError(params);
      params.data[params.colDef.field] = params.newValue;
      const value = params.newValue;
      if (params.colDef.required && (value == null || value.toString().length == 0)) {
        this.#setError(params);
      } else if (params.colDef.max_length != null && value.toString().length > params.colDef.max_length) {
        this.#setError(params);
      }
      return true;
    }
  }

  #clearError(params) {
    params.data.__error = params.data?.__error ?? {}
    params.data.__error[params.colDef.field] = false;
  }

  #setError(params) {
    params.data.__error = params.data?.__error ?? {}
    params.data.__error[params.colDef.field] = true;
  }

  #columnTypes = {
    "dropdown": {
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: (params) => {
        return {
          values: params.colDef?.classes?.map(v => v.value) ?? []
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
      cellDataType: "text",
      cellEditor: "agTextCellEditor"
    },
    "number": {
      cellDataType: "number",
      cellEditor: "agNumberCellEditor",
      filter: 'agNumberColumnFilter',
    },
    "checkbox": {
      cellDataType: "boolean",
      cellRenderer: 'agCheckboxCellRenderer',
      valueGetter: (params) => {
        return params.data[params.colDef.field] == 1
      }
    },
    "date": {
      cellDataType: "date"
    }
  }

  connectedCallback() {
    this.#setupAgGrid();
  }

  async #fetchOption() {
    if (!this.#agGridOptions) {
      this.#agGridOptions = await runFetch(`/getColumns`)
    }
    return this.#agGridOptions;
  }

  async #convertToAgGridColumnDefs(columnOptions) {
    const columnDefs = []
    for (const colOpt of columnOptions) {
      const colDef = { ...colOpt }
      delete colDef.editable
      colDef.headerName = colOpt.column_name
      colDef.field = colOpt.column_cd
      colDef.isEditable = colOpt.editable
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
      rowSelection: {
        mode: 'multiRow',
      },
      columnTypes: this.#columnTypes,
      getRowStyle: params => {
        const style = {}
        for (const rowStyle of (rowStyles ?? [])) {
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
    const addButton = document.createElement("button")
    addButton.textContent = "追加"
    addButton.addEventListener("click", () => this.addRow())
    this.append(addButton)

    const deleteButton = document.createElement("button")
    deleteButton.textContent = "削除"
    deleteButton.addEventListener("click", () => this.deleteRow())
    this.append(deleteButton)

    const agGridDiv = document.createElement("div")
    agGridDiv.style.height = "90%";
    this.append(agGridDiv)

    this.#agGridApi = agGrid.createGrid(agGridDiv, gridOptions);
  }

  addRow() {
    this.#agGridApi.applyTransaction({
      add: [{ __isInserted: true }]
    });
  }

  deleteRow() {
    const deletedItems = this.#agGridApi.getSelectedRows().map(d => { d.__isDeleted = !d.__isDeleted; return d })
    this.#agGridApi.applyTransaction({
      update: deletedItems
    });
  }

  setRowData(rowData) {
    const originalData = JSON.parse(JSON.stringify(rowData));
    this.#originalData = new Map();
    for (const d of originalData) {
      this.#originalData.set(d.id, d);
    }
    this.#agGridApi.setGridOption('rowData', rowData);
    this.#agGridApi.sizeColumnsToFit()
  }

  getUpdateData() {
    const errorList = []
    this.#agGridApi.forEachNode((node) => {
      const data = node.data
      if (data.__error) {
        for (const [k, v] of Object.entries(data.__error)) {
          if (v) {
            errorList.push([data.id, k])
            continue
          }
        }
      }
    })
    if (errorList.length > 0) {
      return { type: 'error', errorList }
    }

    const insertList = []
    const deleteList = []
    const updateList = []
    this.#agGridApi.forEachNode((node) => {
      const data = node.data
      if (data.__isDeleted) {
        if (data.id !== undefined) {
          deleteList.push(data.id)
        }
      } else if (data.__isInserted) {
        const newData = {}
        for (const [k, v] of Object.entries(data)) {
          if (k.startsWith("__")) {
            continue
          }
          newData[k] = v
        }
        insertList.push(newData)
      } else if (data.__isUpdated) {
        const updateData = {}
        const beforeData = this.#originalData.get(data.id);
        for (const [colKey, colValue] of Object.entries(data)) {
          if (colKey.startsWith("__")) {
            continue
          }
          const beforeValue = beforeData?.[colKey]
          if (colValue != beforeValue) {
            updateData[colKey] = colValue
          }
        }
        if (Object.keys(updateData).length > 0) {
          updateData.id = data.id;
          updateList.push(updateData)
        }
      }
    });
    if (insertList.length == 0 && deleteList.length == 0 && updateList.length == 0) {
      return { type: 'nothing' }
    }
    return { type: 'ok', insertList, deleteList, updateList }

  }
}

customElements.define('ag-grid', AgGridDiv, { extends: "div" });
