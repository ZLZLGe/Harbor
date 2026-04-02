import { promises as fs } from "node:fs";
import path from "node:path";
import type { DiscoveredSkill, DiscoveredSubcategory } from "./types.js";
import { compareStringsAscending } from "./utils.js";

function parseRankAndSkillId(directoryName: string): { rank: number | null; skillId: string } {
  const match = /^(\d+)__(.+)$/.exec(directoryName);
  if (!match) {
    return {
      rank: null,
      skillId: directoryName,
    };
  }
  return {
    rank: Number(match[1]),
    skillId: match[2],
  };
}

export async function discoverSkills(subcategoryDir: string): Promise<DiscoveredSkill[]> {
  const absoluteSubcategoryDir = path.resolve(subcategoryDir);
  const stat = await fs.stat(absoluteSubcategoryDir);
  if (!stat.isDirectory()) {
    throw new Error(`小类目录不是有效目录: ${absoluteSubcategoryDir}`);
  }

  const categorySlug = path.basename(path.dirname(absoluteSubcategoryDir));
  const subcategorySlug = path.basename(absoluteSubcategoryDir);
  const entries = await fs.readdir(absoluteSubcategoryDir, { withFileTypes: true });
  const skills = entries
    .filter((entry) => entry.isDirectory())
    .sort((left, right) => compareStringsAscending(left.name, right.name))
    .map((entry) => {
      const parsed = parseRankAndSkillId(entry.name);
      const absolutePath = path.join(absoluteSubcategoryDir, entry.name);
      return {
        categorySlug,
        subcategorySlug,
        directoryName: entry.name,
        skillId: parsed.skillId,
        absolutePath,
        relativePath: `${categorySlug}/${subcategorySlug}/${entry.name}`,
        rank: parsed.rank,
      } satisfies DiscoveredSkill;
    });

  return skills;
}

async function listChildDirectories(directory: string): Promise<string[]> {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort(compareStringsAscending);
}

async function childDirectoryLooksLikeSkill(directory: string): Promise<boolean> {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  if (/^\d+__.+$/.test(path.basename(directory))) {
    return true;
  }
  return entries.some((entry) => entry.isFile() || entry.isSymbolicLink());
}

async function classifyBatchInputDirectory(absoluteInputDir: string): Promise<"root" | "category" | "subcategory"> {
  const childDirectories = await listChildDirectories(absoluteInputDir);
  if (childDirectories.length === 0) {
    throw new Error(`输入目录下没有可发现的子目录: ${absoluteInputDir}`);
  }

  const sampleChildDirectories = childDirectories.slice(0, 5);
  const directChildSkillSignals = await Promise.all(
    sampleChildDirectories.map((directoryName) => childDirectoryLooksLikeSkill(path.join(absoluteInputDir, directoryName))),
  );

  if (directChildSkillSignals.some(Boolean)) {
    return "subcategory";
  }

  for (const directoryName of sampleChildDirectories) {
    const childDir = path.join(absoluteInputDir, directoryName);
    const grandchildDirectories = await listChildDirectories(childDir);
    if (grandchildDirectories.length === 0) {
      continue;
    }

    const grandchildSignals = await Promise.all(
      grandchildDirectories
        .slice(0, 5)
        .map((grandchildName) => childDirectoryLooksLikeSkill(path.join(childDir, grandchildName))),
    );

    if (grandchildSignals.some(Boolean)) {
      return "category";
    }
  }

  return "root";
}

function buildDiscoveredSubcategory(categorySlug: string, subcategorySlug: string, absolutePath: string): DiscoveredSubcategory {
  return {
    categorySlug,
    subcategorySlug,
    absolutePath,
    relativePath: `${categorySlug}/${subcategorySlug}`,
  };
}

export async function discoverSubcategories(inputDir: string): Promise<DiscoveredSubcategory[]> {
  const absoluteInputDir = path.resolve(inputDir);
  const stat = await fs.stat(absoluteInputDir);
  if (!stat.isDirectory()) {
    throw new Error(`输入目录不是有效目录: ${absoluteInputDir}`);
  }

  const inputKind = await classifyBatchInputDirectory(absoluteInputDir);
  if (inputKind === "subcategory") {
    throw new Error(`--input-dir 不能直接指向小类目录: ${absoluteInputDir}；请改用 --subcategory-dir`);
  }

  if (inputKind === "category") {
    const categorySlug = path.basename(absoluteInputDir);
    const subcategoryDirectories = await listChildDirectories(absoluteInputDir);
    return subcategoryDirectories.map((subcategorySlug) =>
      buildDiscoveredSubcategory(categorySlug, subcategorySlug, path.join(absoluteInputDir, subcategorySlug)),
    );
  }

  const categoryDirectories = await listChildDirectories(absoluteInputDir);
  const discoveredSubcategories: DiscoveredSubcategory[] = [];

  for (const categorySlug of categoryDirectories) {
    const absoluteCategoryDir = path.join(absoluteInputDir, categorySlug);
    const subcategoryDirectories = await listChildDirectories(absoluteCategoryDir);
    for (const subcategorySlug of subcategoryDirectories) {
      discoveredSubcategories.push(
        buildDiscoveredSubcategory(categorySlug, subcategorySlug, path.join(absoluteCategoryDir, subcategorySlug)),
      );
    }
  }

  return discoveredSubcategories.sort((left, right) => {
    const categoryDelta = compareStringsAscending(left.categorySlug, right.categorySlug);
    if (categoryDelta !== 0) {
      return categoryDelta;
    }
    return compareStringsAscending(left.subcategorySlug, right.subcategorySlug);
  });
}
