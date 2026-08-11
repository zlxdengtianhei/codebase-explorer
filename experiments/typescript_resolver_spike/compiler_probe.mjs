import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import ts from "typescript";

const root = path.resolve(process.argv[2]);
const configPath = process.argv[3]
  ? path.resolve(process.argv[3])
  : ts.findConfigFile(root, ts.sys.fileExists, "tsconfig.json");
if (!configPath) throw new Error(`tsconfig.json not found below ${root}`);

const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
if (configFile.error) throw new Error(ts.flattenDiagnosticMessageText(configFile.error.messageText, "\n"));
const parsed = ts.parseJsonConfigFileContent(configFile.config, ts.sys, path.dirname(configPath));
const started = process.hrtime.bigint();
const program = ts.createProgram({rootNames: parsed.fileNames, options: parsed.options});
const checker = program.getTypeChecker();
const semanticDiagnostics = program.getSemanticDiagnostics();
const syntacticDiagnostics = program.getSyntacticDiagnostics();

const canonical = (filename) => path.relative(root, path.resolve(filename)).split(path.sep).join("/");
const lineSpan = (sourceFile, node) => {
  const text = sourceFile.text;
  const line = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line;
  const starts = sourceFile.getLineStarts();
  const start = starts[line];
  let end = line + 1 < starts.length ? starts[line + 1] - 1 : text.length;
  if (text[end - 1] === "\r") end -= 1;
  const fragment = text.slice(start, end);
  return {
    path: canonical(sourceFile.fileName),
    byte_offset: Buffer.byteLength(text.slice(0, start), "utf8"),
    byte_length: Buffer.byteLength(fragment, "utf8"),
    line: line + 1,
    column: 0,
    text: fragment,
  };
};
const visit = (node, predicate) => {
  if (predicate(node)) return node;
  let found;
  node.forEachChild((child) => { if (!found) found = visit(child, predicate); });
  return found;
};
const source = (suffix) => program.getSourceFiles().find((f) => canonical(f.fileName) === suffix);
const aliasTarget = (symbol) => symbol && (symbol.flags & ts.SymbolFlags.Alias) ? checker.getAliasedSymbol(symbol) : symbol;
const declarationTarget = (symbol) => {
  const target = aliasTarget(symbol);
  const decl = target?.declarations?.[0];
  if (!target || !decl) return null;
  return {name: checker.getFullyQualifiedName(target), path: canonical(decl.getSourceFile().fileName)};
};

const facts = {};
const base = source("src/base.ts");
const impl = source("src/impl.ts");
const index = source("src/index.ts");
if (base) {
  const runner = visit(base, (n) => ts.isInterfaceDeclaration(n) && n.name.text === "Runner");
  const method = runner?.members.find((m) => ts.isMethodSignature(m) && m.name.getText(base) === "run");
  const signature = method ? checker.getSignatureFromDeclaration(method) : undefined;
  facts["ts.type.runner.run"] = method && signature ? {
    observed: true,
    target: checker.typeToString(checker.getReturnTypeOfSignature(signature)),
    resolution_method: "compiler",
    span: lineSpan(base, method),
  } : {observed: false};
}
if (impl) {
  const worker = visit(impl, (n) => ts.isClassDeclaration(n) && n.name?.text === "Worker");
  const heritage = worker?.heritageClauses?.find((h) => h.token === ts.SyntaxKind.ImplementsKeyword)?.types[0];
  const target = heritage ? declarationTarget(checker.getSymbolAtLocation(heritage.expression)) : null;
  facts["ts.implements.worker"] = worker && heritage ? {
    observed: true,
    target,
    resolution_method: "compiler",
    span: lineSpan(impl, worker),
  } : {observed: false};
}
if (index) {
  const call = visit(index, (n) => ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression)
    && n.expression.getText(index) === "worker.run");
  const signature = call ? checker.getResolvedSignature(call) : undefined;
  const target = call ? declarationTarget(checker.getSymbolAtLocation(call.expression.name)) : null;
  const receiverType = call ? checker.typeToString(checker.getTypeAtLocation(call.expression.expression)) : null;
  facts["ts.call.worker.run"] = call ? {
    observed: true,
    target,
    receiver_type: receiverType,
    resolution_method: "compiler",
    span: lineSpan(index, call),
  } : {observed: false};
}

const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6;
const diagnostics = [...syntacticDiagnostics, ...semanticDiagnostics].map((d) => ({
  code: d.code,
  category: ts.DiagnosticCategory[d.category],
  path: d.file ? canonical(d.file.fileName) : null,
  message: ts.flattenDiagnosticMessageText(d.messageText, "\n"),
}));
console.log(JSON.stringify({
  candidate: "typescript_compiler_api",
  typescript_version: ts.version,
  root,
  config_path: configPath,
  root_file_count: parsed.fileNames.length,
  program_source_file_count: program.getSourceFiles().length,
  elapsed_ms: elapsedMs,
  rss_bytes: process.memoryUsage().rss,
  heap_used_bytes: process.memoryUsage().heapUsed,
  facts,
  diagnostic_count: diagnostics.length,
  diagnostics: diagnostics.slice(0, 50),
}, null, 2));
