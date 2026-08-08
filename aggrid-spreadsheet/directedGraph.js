export class DirectedGraph {
  constructor() {
    // 順方向: from -> Set(to)
    this.outEdges = new Map();
    // 逆方向: to -> Set(from)
    this.inEdges = new Map();
  }

  /**
   * ノードの存在を保証
   */
  _ensureNode(node) {
    if (!this.outEdges.has(node)) {
      this.outEdges.set(node, new Set());
    }
    if (!this.inEdges.has(node)) {
      this.inEdges.set(node, new Set());
    }
  }

  /**
   * 依存関係の追加 (from -> to)
   */
  addEdge(from, to) {
    this._ensureNode(from);
    this._ensureNode(to);
    this.outEdges.get(from).add(to);
    this.inEdges.get(to).add(from);
  }

  /**
   * 特定の依存関係 (from -> to) のみを削除
   */
  removeEdge(from, to) {
    if (from === undefined || to === undefined) return;

    this.outEdges.get(from)?.delete(to);
    this.inEdges.get(to)?.delete(from);
  }

  /**
   * 指定したノードから出る辺をすべて削除 (from -> *)
   */
  removeOutgoingEdges(from) {
    const targets = this.outEdges.get(from);
    if (!targets) return;

    for (const target of targets) {
      this.inEdges.get(target)?.delete(from);
    }
    targets.clear();
  }

  /**
   * 指定したノードに入る辺をすべて削除 (* -> to)
   */
  removeIncomingEdges(to) {
    const sources = this.inEdges.get(to);
    if (!sources) return;

    for (const source of sources) {
      this.outEdges.get(source)?.delete(to);
    }
    sources.clear();
  }

  /**
   * 特定ノードからの依存先を更新
   */
  updateEdges(from, newToNodes) {
    // 既存の出辺を一度すべて削除して逆方向Mapの整合性を保つ
    this.removeOutgoingEdges(from);

    this._ensureNode(from);
    for (const to of newToNodes) {
      this.addEdge(from, to);
    }
  }

  /**
   * ノードそのものを削除（接続する辺もすべて削除）
   */
  removeNode(node) {
    if (!this.outEdges.has(node)) return;

    // 出る辺・入る辺を削除
    this.removeOutgoingEdges(node);
    this.removeIncomingEdges(node);

    this.outEdges.delete(node);
    this.inEdges.delete(node);
  }

  /**
   * 指定したノード群（誘導部分グラフ）に対してトポロジカルソートを実行
   * @param {Set<any>} [targetNodes] 対象ノード集合。省略時は全ノード
   */
  topologicalSort(targetNodes = null) {
    const nodes = targetNodes ?? new Set(this.outEdges.keys());
    const inDegrees = this._calculateInDegrees(nodes, targetNodes !== null);

    return this._sortNodesByInDegree(nodes, inDegrees, targetNodes);
  }

  /**
   * 指定した変更ノード群から影響を受けるノードのみ抽出し、
   * 再計算すべき順序を取得する
   * @param {Iterable<any>} changedNodes 変更のあった起点ノード群
   */
  getEvaluationOrder(changedNodes) {
    const affected = this._getAffectedNodes(changedNodes);
    return this.topologicalSort(affected);
  }

  // --- 再計算・ソート用内部ヘルパー関数 ---

  /**
   * 変更点から到達可能なすべてのノード（影響範囲）を収集 (BFS)
   */
  _getAffectedNodes(startNodes) {
    const affected = new Set();
    const queue = [];

    for (const node of startNodes) {
      if (this.outEdges.has(node) && !affected.has(node)) {
        affected.add(node);
        queue.push(node);
      }
    }

    let head = 0;
    while (head < queue.length) {
      const current = queue[head++];
      const neighbors = this.outEdges.get(current);
      if (neighbors) {
        for (const neighbor of neighbors) {
          if (!affected.has(neighbor)) {
            affected.add(neighbor);
            queue.push(neighbor);
          }
        }
      }
    }

    return affected;
  }

  /**
   * 対象ノード群に対する（部分グラフ内の）入次数を計算
   */
  _calculateInDegrees(nodes, isSubset) {
    const inDegree = new Map();

    for (const node of nodes) {
      const sources = this.inEdges.get(node);
      let count = 0;

      if (sources) {
        if (isSubset) {
          for (const source of sources) {
            if (nodes.has(source)) count++;
          }
        } else {
          count = sources.size;
        }
      }

      inDegree.set(node, count);
    }

    return inDegree;
  }

  /**
   * 入次数をもとにトポロジカルソートを実行 (Kahn's Algorithm)
   */
  _sortNodesByInDegree(nodes, inDegree, targetNodes) {
    const queue = [];

    // 入次数 0 のノードを初期キューに投入
    for (const [node, degree] of inDegree) {
      if (degree === 0) {
        queue.push(node);
      }
    }

    let head = 0;

    const result = []

    while (head < queue.length) {
      const current = queue[head++];

      result.push(current)

      const neighbors = this.outEdges.get(current);
      if (neighbors) {
        for (const neighbor of neighbors) {
          if (targetNodes !== null && !targetNodes.has(neighbor)) continue;

          const updatedDegree = inDegree.get(neighbor) - 1;
          inDegree.set(neighbor, updatedDegree);

          if (updatedDegree === 0) {
            queue.push(neighbor);
          }
        }
      }
    }

    if (result.length !== nodes.size) {
      throw new Error("Graph contains a cycle (circular dependency).");
    }
    return result;
  }
}
