import path from "node:path";
import { parseArgs } from "node:util";
import { fileURLToPath } from "node:url";
import { runSkillScreening } from "./runner.js";
import type { BatchRunOptions, SingleRunOptions } from "./types.js";
import { parsePositiveInteger } from "./utils.js";

function printHelp(): void {
  console.log(`Usage:
  node --import tsx src/cli.ts \\
    --input-dir /mnt/e/skill_all/development \\
    --output-dir /mnt/e/skill_screening_runs/development \\
    [--model gpt-5.4] [--jobs 4] [--limit 10] [--resume] [--overwrite]

Single-subcategory mode:
  node --import tsx src/cli.ts \\
    --subcategory-dir /mnt/e/skill_all/development/backend \\
    --output-dir /mnt/e/skill_screening_runs/development__backend \\
    [--model gpt-5.4] [--jobs 4] [--limit 10] [--resume] [--overwrite]

Options:
  --input-dir         批量输入目录（总根目录或单个大类目录）
  --subcategory-dir   单小类输入目录
  --output-dir        结果输出目录（批量模式下为根目录）
  --model             可选，覆盖默认模型
  --jobs              并发数，默认 4
  --limit             批量模式下按每个小类只跑前 N 个 skill
  --resume            跳过已有结果
  --overwrite         先清空输出目录
  --prompt-path       覆盖默认 prompt 资产
  --schema-path       覆盖默认 schema 资产
  --help              显示帮助
`);
}

export function buildRunOptionsFromArgv(argv: string[]): SingleRunOptions | BatchRunOptions {
  const { values } = parseArgs({
    args: argv,
    options: {
      "input-dir": { type: "string" },
      "subcategory-dir": { type: "string" },
      "output-dir": { type: "string" },
      model: { type: "string" },
      jobs: { type: "string" },
      limit: { type: "string" },
      resume: { type: "boolean" },
      overwrite: { type: "boolean" },
      "prompt-path": { type: "string" },
      "schema-path": { type: "string" },
      help: { type: "boolean" },
    },
    allowPositionals: false,
  });

  if (values.help) {
    printHelp();
    process.exit(0);
  }

  if (values["input-dir"] && values["subcategory-dir"]) {
    throw new Error("--input-dir 和 --subcategory-dir 不能同时使用");
  }
  if (!values["output-dir"]) {
    throw new Error("缺少必填参数 --output-dir");
  }
  if (!values["input-dir"] && !values["subcategory-dir"]) {
    throw new Error("必须提供 --input-dir 或 --subcategory-dir 其中之一");
  }
  if (values.resume && values.overwrite) {
    throw new Error("--resume 和 --overwrite 不能同时使用");
  }

  const baseOptions = {
    outputDir: values["output-dir"],
    model: values.model,
    jobs: values.jobs ? parsePositiveInteger(values.jobs, "--jobs") : 4,
    limit: values.limit ? parsePositiveInteger(values.limit, "--limit") : undefined,
    resume: values.resume ?? false,
    overwrite: values.overwrite ?? false,
    promptPath: values["prompt-path"],
    schemaPath: values["schema-path"],
  };

  if (values["input-dir"]) {
    return {
      mode: "batch",
      inputDir: values["input-dir"],
      ...baseOptions,
    };
  }

  return {
    mode: "single",
    subcategoryDir: values["subcategory-dir"] as string,
    ...baseOptions,
  };
}

async function main(): Promise<void> {
  const options = buildRunOptionsFromArgv(process.argv.slice(2));
  const result = await runSkillScreening(options);

  if (result.mode === "batch") {
    console.log(
      JSON.stringify(
        {
          output_dir: result.summary.output_dir,
          subcategories_processed: result.summary.total_subcategories_processed,
          keep: result.summary.decision_counts.keep,
          drop: result.summary.decision_counts.drop,
          failures: result.summary.total_failures,
          total_results: result.summary.total_results,
        },
        null,
        2,
      ),
    );
    return;
  }

  console.log(
    JSON.stringify(
      {
        output_dir: result.summary.output_dir,
        keep: result.summary.decision_counts.keep,
        drop: result.summary.decision_counts.drop,
        failures: result.summary.total_failures,
        total_results: result.summary.total_results,
      },
      null,
      2,
    ),
  );
}

const currentFilePath = fileURLToPath(import.meta.url);
const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";

if (invokedPath === currentFilePath) {
  void main().catch((error: unknown) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(message);
    process.exitCode = 1;
  });
}
