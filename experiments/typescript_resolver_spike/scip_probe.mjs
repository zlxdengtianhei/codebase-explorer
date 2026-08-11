import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { scip } from "@sourcegraph/scip-typescript/dist/src/scip.js";

const root = path.resolve(process.argv[2]);
const indexPath = path.resolve(process.argv[3]);
const started = process.hrtime.bigint();
const index = scip.Index.deserializeBinary(fs.readFileSync(indexPath)).toObject();
const document = (relativePath) => index.documents.find((item) => item.relative_path === relativePath);
const lineSpan = (relativePath, oneBasedLine) => {
  const text = fs.readFileSync(path.join(root, relativePath), "utf8");
  const lines = text.split("\n");
  const prefix = lines.slice(0, oneBasedLine - 1).join("\n") + (oneBasedLine > 1 ? "\n" : "");
  return {
    path: relativePath,
    byte_offset: Buffer.byteLength(prefix, "utf8"),
    byte_length: Buffer.byteLength(lines[oneBasedLine - 1], "utf8"),
    line: oneBasedLine,
    column: 0,
    text: lines[oneBasedLine - 1],
  };
};
const occurrenceAt = (doc, line0, start, end) => doc?.occurrences.find((item) =>
  item.range[0] === line0 && item.range.at(-2) === start && item.range.at(-1) === end);
const symbolInfo = (symbol) => index.documents.flatMap((doc) => doc.symbols)
  .find((item) => item.symbol === symbol);

const base = document("src/base.ts");
const impl = document("src/impl.ts");
const entry = document("src/index.ts");
const runDefinition = occurrenceAt(base, 1, 2, 5);
const runnerImplementationReference = occurrenceAt(impl, 1, 31, 37);
const callReference = occurrenceAt(entry, 5, 9, 12);
const runInfo = symbolInfo(runDefinition?.symbol);

const facts = {
  "ts.type.runner.run": runDefinition && runInfo ? {
    observed: true,
    target: /(?:=>|:)\s*string\b/.test(runInfo.documentation.join("\n")) ? "string" : null,
    evidence_surface: "symbol documentation string (not a typed result field)",
    symbol: runDefinition.symbol,
    span: lineSpan("src/base.ts", 2),
  } : {observed: false},
  "ts.implements.worker": runnerImplementationReference ? {
    observed: !runnerImplementationReference.symbol.startsWith("local "),
    symbol: runnerImplementationReference.symbol,
    evidence_surface: "identifier occurrence only; SCIP carries no implements edge for this fixture",
    span: lineSpan("src/impl.ts", 2),
  } : {observed: false},
  "ts.call.worker.run": callReference ? {
    observed: !callReference.symbol.startsWith("local "),
    symbol: callReference.symbol,
    evidence_surface: "callee occurrence symbol, not an explicit call edge",
    span: lineSpan("src/index.ts", 6),
  } : {observed: false},
};

console.log(JSON.stringify({
  candidate: "scip_typescript",
  scip_typescript_version: index.metadata.tool_info.version,
  project_root: index.metadata.project_root,
  document_count: index.documents.length,
  occurrence_count: index.documents.reduce((sum, doc) => sum + doc.occurrences.length, 0),
  symbol_count: index.documents.reduce((sum, doc) => sum + doc.symbols.length, 0),
  elapsed_ms: Number(process.hrtime.bigint() - started) / 1e6,
  rss_bytes: process.memoryUsage().rss,
  facts,
}, null, 2));
