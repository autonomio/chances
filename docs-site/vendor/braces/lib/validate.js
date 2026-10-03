'use strict';

const MAX_DEPTH = 100;
const MAX_NODES = 10000;

function validate(ast) {
  const pending = [[ast, 1]];
  const seen = new Set();
  while (pending.length) {
    const [node, depth] = pending.pop();
    if (!node || typeof node !== 'object') throw new TypeError('expected a brace AST node');
    if (depth > MAX_DEPTH) throw new SyntaxError('brace AST exceeds maximum depth');
    if (seen.has(node)) throw new SyntaxError('brace AST contains repeated nodes');
    seen.add(node);
    if (seen.size > MAX_NODES) throw new SyntaxError('brace AST exceeds maximum node count');
    if (node.nodes !== undefined) {
      if (!Array.isArray(node.nodes)) throw new TypeError('expected brace AST children array');
      if (node.nodes.length + seen.size + pending.length > MAX_NODES) {
        throw new SyntaxError('brace AST exceeds maximum node count');
      }
      for (const child of node.nodes) pending.push([child, depth + 1]);
    }
  }
}

module.exports = { MAX_DEPTH, validate };
