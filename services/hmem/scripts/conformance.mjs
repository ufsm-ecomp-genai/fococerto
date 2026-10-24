// Roda a suíte de conformidade oficial do H-MEM (conformance/runner.ts, copiada
// sem alterações do repositório da Meterless) contra o NOSSO engine
// (src/engine/index.ts, o mesmo que o servidor usa) e salva a saída em
// conformance-report.txt. Sai com o código do runner (0 = tudo passou).
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const impl = path.join(raiz, "src", "engine", "index.ts");
const tsx = path.join(raiz, "node_modules", ".bin", process.platform === "win32" ? "tsx.cmd" : "tsx");
const r = spawnSync(tsx, [path.join(raiz, "conformance", "runner.ts")], {
  cwd: raiz,
  env: { ...process.env, HMEM_IMPL: impl },
  encoding: "utf-8",
});
const cabecalho = [
  "FocoCerto H-MEM: relatório da suíte de conformidade oficial",
  `data: ${new Date().toISOString()}`,
  `node: ${process.version}`,
  "suíte: conformance/runner.ts + conformance/vectors/vectors.json (cópia sem alterações, Meterless, Apache-2.0)",
  `implementação: src/engine/index.ts (HMEM_IMPL=${path.relative(raiz, impl)})`,
  `código de saída do runner: ${r.status}`,
  "",
].join("\n");
const saida = (r.stdout ?? "").replaceAll(raiz + path.sep, "") + (r.stderr ? `\n[stderr]\n${r.stderr}` : "");
fs.writeFileSync(path.join(raiz, "conformance-report.txt"), cabecalho + saida, "utf-8");
process.stdout.write(saida);
process.exit(r.status ?? 2);
