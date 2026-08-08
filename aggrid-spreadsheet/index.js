import { DirectedGraph } from "/directedGraph.js"
const columnNum = 5;
const rowNum = 10;

function makeGrid(grid) {
  for (let rowid = 0; rowid < rowNum; rowid++) {
    const rowElm = document.createElement("div")
    rowElm.classList.add("row")
    grid.append(rowElm)
    for (let colid = 0; colid < columnNum; colid++) {
      const cellElm = document.createElement("input")
      cellElm.classList.add("col")
      cellElm.dataset.rowid = rowid;
      cellElm.dataset.colid = colid;
      rowElm.append(cellElm)
      const cacheElm = document.createElement("span")
      cacheElm.classList.add("col")
      cacheElm.classList.add("cache")
      cacheElm.dataset.rowid = rowid;
      cacheElm.dataset.colid = colid;
      rowElm.append(cacheElm)
    }
  }
}


const grid = document.querySelector("#myGrid");
makeGrid(grid);

const graph = new DirectedGraph()

function getCell(rowid, colid) {
  return grid.querySelector(`input.col[data-rowid="${rowid}"][data-colid="${colid}"]`)
}

function getCache(rowid, colid) {
  return grid.querySelector(`span.col.cache[data-rowid="${rowid}"][data-colid="${colid}"]`)
}

function getDependsOn(value) {
  const re = /cell[(]\s*(?<rowid>\d+)\s*,\s*(?<colid>\d+)[)]/g
  const out = []
  for (const m of value.matchAll(re)) {
    const depCell = m.groups;
    out.push(depCell);
  }
  return out
}

function registerCell(cell) {
  graph.removeIncomingEdges(cell);
  const value = cell.value
  graph._ensureNode(cell)
  const dependsOn = getDependsOn(value);
  for (const { rowid: depRowid, colid: depColid } of dependsOn) {
    const depCell = getCell(depRowid, depColid)
    graph.addEdge(depCell, cell)
  }
}

function getCellName(cell) {
  const { rowid, colid } = cell.dataset;
  return `rowid=${rowid},colid=${colid}`
}

function evaluateCell(calcCell) {
  console.log('eval', getCellName(calcCell))
  const value = calcCell.value;
  if (!value?.startsWith?.("=")) {
    return value;
  }
  try {
    const cell = (rowid, colid) => {
      return getCache(rowid, colid).textContent
    }

    return Function("cell", `"use strict";return (${value.substring(1)});`)(cell)
  } catch (e) {
    return "ERROR: " + e.toString();
  }
}

function calcFromThisCell(cell) {
  try {
    for (const evalCell of graph.getEvaluationOrder([cell])) {
      const { rowid, colid } = evalCell.dataset;
      const newValue = evaluateCell(evalCell);
      const oldValue = getCache(rowid, colid).textContent
      if (newValue != oldValue) {
        getCache(rowid, colid).textContent = newValue;
      }
    }
  } catch (e) {
    const { rowid, colid } = cell.dataset
    getCache(rowid, colid).textContent = "ERROR: " + e.toString();
  }
}

grid.addEventListener('change', (event) => {
  const cell = event.target;
  registerCell(cell);
  calcFromThisCell(cell);
})

