/**
 * OpenAPI 类型按模块拆分生成脚本
 *
 * 从后端 OpenAPI schema 按 tag 拆分生成多个类型文件，
 * 通过 index.ts 统一导出，对 schema.ts 等消费方透明。
 *
 * 用法：
 *   npm run gen:types                    # 生成类型
 *   npm run gen:types -- --check         # 仅检查（不写入文件）
 *   npm run gen:types -- --input schema.json  # 从本地文件读取
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import openapiTS, { astToString, COMMENT_HEADER } from 'openapi-typescript';

// ============ 常量 ============

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CLIENT_ROOT = path.resolve(__dirname, '..');
const GENERATED_DIR = path.resolve(CLIENT_ROOT, 'src/types/generated');
const DEFAULT_API_URL = 'http://localhost:8000/api/v1/openapi.json';

/** 模块名称 */
const MODULES = ['market', 'analysis', 'trading', 'system'] as const;
type ModuleName = (typeof MODULES)[number];

/** Tag → 模块映射 */
const TAG_MODULE_MAP: Record<string, ModuleName> = {
  // market
  Market: 'market',
  'North Money': 'market',
  龙虎榜: 'market',
  限售解禁: 'market',
  跨资产联动分析: 'market',
  'Market Watcher': 'market',
  'Alternative Data': 'market',
  // analysis
  Analysis: 'analysis',
  Sentiment: 'analysis',
  Macro: 'analysis',
  '央行 NLP 分析': 'analysis',
  Policy: 'analysis',
  Reflection: 'analysis',
  'Model Racing': 'analysis',
  'Vision Analysis': 'analysis',
  'Supply Chain': 'analysis',
  // trading
  Watchlist: 'trading',
  News: 'trading',
  'News Aggregator': 'trading',
  Chat: 'trading',
  Memory: 'trading',
  Portfolio: 'trading',
  Discovery: 'trading',
  Backtest: 'trading',
  // system
  Authentication: 'system',
  OAuth: 'system',
  Passkey: 'system',
  'Health Monitor': 'system',
  'AI Configuration': 'system',
  'Prompt Config': 'system',
  Settings: 'system',
  TTS: 'system',
  Admin: 'system',
};

// ============ 类型 ============

interface OpenAPISchema {
  openapi: string;
  info: Record<string, unknown>;
  paths?: Record<string, Record<string, unknown>>;
  components?: Record<string, unknown>;
  [key: string]: unknown;
}

interface GeneratedFile {
  name: string;
  content: string;
}

// ============ 工具函数 ============

/** 解析命令行参数 */
function parseArgs(): { check: boolean; input?: string } {
  const args = process.argv.slice(2);
  return {
    check: args.includes('--check'),
    input: args.find((_, i, a) => a[i - 1] === '--input'),
  };
}

/** 获取 OpenAPI schema */
async function fetchSchema(input?: string): Promise<OpenAPISchema> {
  if (input) {
    const filePath = path.resolve(process.cwd(), input);
    console.log(`📄 从本地文件读取: ${filePath}`);
    const content = fs.readFileSync(filePath, 'utf-8');
    return JSON.parse(content);
  }

  console.log(`🌐 从后端获取 schema: ${DEFAULT_API_URL}`);
  const response = await fetch(DEFAULT_API_URL);
  if (!response.ok) {
    throw new Error(
      `获取 OpenAPI schema 失败: ${response.status} ${response.statusText}\n` +
        `请确保后端已启动: cd apps/server && python main.py`,
    );
  }
  return response.json();
}

/** 根据 tag 确定 path 所属模块 */
function resolveModule(pathItem: Record<string, unknown>): ModuleName | null {
  const methods = ['get', 'post', 'put', 'delete', 'patch', 'options', 'head'];
  for (const method of methods) {
    const operation = pathItem[method] as Record<string, unknown> | undefined;
    if (operation?.tags && Array.isArray(operation.tags) && operation.tags.length > 0) {
      const tag = operation.tags[0] as string;
      const mod = TAG_MODULE_MAP[tag];
      if (mod) return mod;
    }
  }
  return null;
}

/** 按模块拆分 paths */
function splitPathsByModule(
  paths: Record<string, Record<string, unknown>>,
): Record<ModuleName, Record<string, Record<string, unknown>>> {
  const result: Record<ModuleName, Record<string, Record<string, unknown>>> = {
    market: {},
    analysis: {},
    trading: {},
    system: {},
  };

  const unmapped: string[] = [];

  for (const [pathKey, pathItem] of Object.entries(paths)) {
    const mod = resolveModule(pathItem);
    if (mod) {
      result[mod][pathKey] = pathItem;
    } else {
      unmapped.push(pathKey);
      // 未映射的 path 放入 system 模块（如 / 和 /health）
      result.system[pathKey] = pathItem;
    }
  }

  if (unmapped.length > 0) {
    console.log(`⚠️  ${unmapped.length} 个 path 未匹配 tag，已归入 system 模块:`);
    unmapped.forEach((p) => console.log(`   - ${p}`));
  }

  return result;
}

/** 为模块构造独立的 OpenAPI sub-schema */
function buildSubSchema(
  original: OpenAPISchema,
  modulePaths: Record<string, Record<string, unknown>>,
): OpenAPISchema {
  return {
    openapi: original.openapi,
    info: { ...original.info, title: `${original.info.title} (partial)` },
    paths: modulePaths,
    // 保留完整 components，openapi-typescript 会自动裁剪未引用的
    components: original.components,
  };
}

/** 构造仅包含 components 的 schema（用于 common.ts） */
function buildComponentsOnlySchema(original: OpenAPISchema): OpenAPISchema {
  return {
    openapi: original.openapi,
    info: { ...original.info, title: `${original.info.title} (components)` },
    paths: {},
    components: original.components,
  };
}

/** 调用 openapi-typescript 生成类型字符串 */
async function generateTypeString(schema: OpenAPISchema): Promise<string> {
  const ast = await openapiTS(schema as never, {
    exportType: true,
    alphabetize: false,
  });
  return astToString(ast);
}

/** 生成 index.ts 内容 */
function generateIndexContent(): string {
  const imports = MODULES.map((mod) => {
    const pascal = mod.charAt(0).toUpperCase() + mod.slice(1);
    return `import type { paths as ${pascal}Paths, operations as ${pascal}Ops } from './${mod}';`;
  }).join('\n');

  const pathsUnion = MODULES.map((mod) => {
    const pascal = mod.charAt(0).toUpperCase() + mod.slice(1);
    return `${pascal}Paths`;
  }).join(' & ');

  const opsUnion = MODULES.map((mod) => {
    const pascal = mod.charAt(0).toUpperCase() + mod.slice(1);
    return `${pascal}Ops`;
  }).join(' & ');

  return `${COMMENT_HEADER}
${imports}
export type { components } from './common';

export type paths = ${pathsUnion};
export type operations = ${opsUnion};
`;
}

// ============ 主流程 ============

async function main(): Promise<void> {
  const startTime = Date.now();
  const { check, input } = parseArgs();

  console.log('🚀 OpenAPI 类型按模块拆分生成');
  console.log(`   模式: ${check ? '检查（dry-run）' : '生成'}`);
  console.log('');

  // 1. 获取 schema
  const schema = await fetchSchema(input);
  const pathCount = Object.keys(schema.paths ?? {}).length;
  const schemaCount = Object.keys(
    (schema.components as Record<string, Record<string, unknown>>)?.schemas ?? {},
  ).length;
  console.log(`✅ Schema 加载完成: ${pathCount} paths, ${schemaCount} schemas`);

  // 2. 按模块拆分 paths
  const modulePathsMap = splitPathsByModule(schema.paths ?? {});
  for (const mod of MODULES) {
    const count = Object.keys(modulePathsMap[mod]).length;
    console.log(`   📦 ${mod}: ${count} paths`);
  }
  console.log('');

  // 3. 并行生成各模块类型
  console.log('⏳ 生成类型文件...');

  const files: GeneratedFile[] = [];

  // 3a. 生成 common.ts（仅 components）
  const commonSchema = buildComponentsOnlySchema(schema);
  const commonPromise = generateTypeString(commonSchema).then((content) => {
    files.push({ name: 'common.ts', content: COMMENT_HEADER + content });
    console.log(`   ✅ common.ts (components)`);
  });

  // 3b. 并行生成各模块
  const modulePromises = MODULES.map(async (mod) => {
    const subSchema = buildSubSchema(schema, modulePathsMap[mod]);
    const content = await generateTypeString(subSchema);
    files.push({ name: `${mod}.ts`, content: COMMENT_HEADER + content });
    console.log(`   ✅ ${mod}.ts`);
  });

  await Promise.all([commonPromise, ...modulePromises]);

  // 3c. 生成 index.ts
  const indexContent = generateIndexContent();
  files.push({ name: 'index.ts', content: indexContent });
  console.log(`   ✅ index.ts`);
  console.log('');

  // 4. 写入文件（或检查模式）
  if (check) {
    console.log('🔍 检查模式 — 不写入文件');
    let hasChanges = false;
    for (const file of files) {
      const filePath = path.join(GENERATED_DIR, file.name);
      if (!fs.existsSync(filePath)) {
        console.log(`   ❌ 缺失: ${file.name}`);
        hasChanges = true;
      } else {
        const existing = fs.readFileSync(filePath, 'utf-8');
        if (existing !== file.content) {
          console.log(`   ❌ 过期: ${file.name}`);
          hasChanges = true;
        } else {
          console.log(`   ✅ 最新: ${file.name}`);
        }
      }
    }
    if (hasChanges) {
      console.log('\n❌ 类型文件需要更新，请运行 npm run gen:types');
      process.exit(1);
    }
    console.log('\n✅ 所有类型文件已是最新');
  } else {
    // 确保目录存在
    fs.mkdirSync(GENERATED_DIR, { recursive: true });

    for (const file of files) {
      const filePath = path.join(GENERATED_DIR, file.name);
      fs.writeFileSync(filePath, file.content, 'utf-8');
    }

    // 统计
    const totalLines = files.reduce((sum, f) => sum + f.content.split('\n').length, 0);
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    console.log(`📊 生成统计:`);
    console.log(`   文件数: ${files.length}`);
    console.log(`   总行数: ${totalLines}`);
    console.log(`   耗时: ${elapsed}s`);
    console.log(`   输出: ${path.relative(CLIENT_ROOT, GENERATED_DIR)}/`);
    console.log('');
    console.log('✅ 类型生成完成！');
  }
}

main().catch((err) => {
  console.error('❌ 生成失败:', err.message ?? err);
  process.exit(1);
});
