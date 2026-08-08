import { DirectedGraph } from "/directedGraph.js"
const columnNum = 20;
const rowNum = 100;

function makeEmptyRowData() {
  const rowData = []
  for (let i = 0; i < rowNum; i++) {
    const row = { rowid: i, cells: [], cache: [] }
    for (let j = 0; j < columnNum; j++) {
      row.cells.push("");
      row.cache.push("");
    }
    rowData.push(row)
  }
  return rowData;
}

function makeColumnDefs() {
  const columnDefs = []
  columnDefs.push({
    headerName: '#',
    field: 'rowid',
    editable: false,
    valueGetter: (params) => {
      return params.data.rowid;
    },
    valueFormatter: (params) => {
      return params.value;
    }
  })
  for (let i = 0; i < columnNum; i++) {
    const ii = i;
    const columnDef = {
      colid: ii,
      headerName: `${i}`,
      editable: true,
    }
    columnDefs.push(columnDef)
  }
  return columnDefs;
}


function evalFunc(api, funcStr) {
  try {
    const cell = (rowid, colid) => {
      return getCacheValue(api, rowid, colid)
    }
    const code = `"use strict";return (${funcStr});`
    return Function("cell", code)(cell)
  } catch (e) {
    return "ERROR: " + e.toString();
  }
}


// セルを評価する
function evaluateCell(rowid, colid) {
  let cellValue = getCellValue(api, rowid, colid);
  let cache;
  if (cellValue && cellValue.startsWith("=")) {
    cache = evalFunc(api, cellValue.substring(1))
  } else {
    cache = cellValue
  }
  // setCacheValue(api, rowid, colid, cache)
}


const defaultColDef = {
  valueGetter: function(params) {
    return params.data.cells[params.colDef.colid];
  },
  valueFormatter: function(params) {
    evaluateCell(params.api, params.data.rowid, params.colDef.colid)
    return params.data.cache[params.colDef.colid] ?? "###";
  },
  valueSetter: function(params) {
    const colid = params.colDef.colid
    delete params.data.cache[colid]
    params.data.cells[colid] = params.newValue;
  },
}


const gridOptions = {
  getRowId: (params) => params.data.rowid,
  rowData: makeEmptyRowData(),
  defaultColDef,
  columnDefs: makeColumnDefs(),
  rowSelection: {
    mode: 'multiRow',
    checkboxes: false,
  },
  context: { directedGraph: new DirectedGraph() },
};

const agGridDiv = document.getElementById("myGrid")
agGridDiv.style.height = "90vh";
agGrid.createGrid(agGridDiv, gridOptions);


