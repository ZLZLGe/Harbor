import fs from "node:fs/promises";
import path from "node:path";

const dataRoot = process.env.DATA_ROOT || "/app/data";

function sumInventory(product) {
  return product.variants.reduce((sum, variant) => sum + Number(variant.inventory || 0), 0);
}

function minPrice(product) {
  return Math.min(...product.variants.map((variant) => Number(variant.price)));
}

function minCompareAtPrice(product) {
  const compareAt = product.variants
    .map((variant) => Number(variant.compare_at_price || 0))
    .filter((value) => value > 0);
  return compareAt.length > 0 ? Math.min(...compareAt) : 0;
}

function availabilityState(product, lowStockThreshold) {
  const total = sumInventory(product);
  if (total <= 0) {
    return { value: "sold_out", label: "Sold out" };
  }
  if (total <= lowStockThreshold) {
    return { value: "low_stock", label: "Low stock" };
  }
  return { value: "in_stock", label: "In stock" };
}

function sortByConfiguredOrder(values, configuredOrder) {
  const ranking = new Map(configuredOrder.map((value, index) => [value, index]));
  return [...values].sort((left, right) => {
    const leftRank = ranking.has(left) ? ranking.get(left) : Number.MAX_SAFE_INTEGER;
    const rightRank = ranking.has(right) ? ranking.get(right) : Number.MAX_SAFE_INTEGER;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return String(left).localeCompare(String(right));
  });
}

export async function loadInputs(root = dataRoot) {
  const readJson = async (name) => JSON.parse(await fs.readFile(path.join(root, name), "utf-8"));
  const [catalog, collectionContext, predictiveSearch, blueprint, qualityRules] = await Promise.all([
    readJson("catalog_products.json"),
    readJson("collection_context.json"),
    readJson("predictive_search_snapshot.json"),
    readJson("theme_section_blueprint.json"),
    readJson("theme_quality_rules.json")
  ]);
  return { catalog, collectionContext, predictiveSearch, blueprint, qualityRules };
}

export function buildCollectionModel(inputs) {
  const { catalog, collectionContext, blueprint } = inputs;
  const orderMap = new Map(collectionContext.product_order.map((handle, index) => [handle, index]));
  const lowStockThreshold = Number(collectionContext.low_stock_threshold);
  const badges = collectionContext.badge_labels;
  const selectedProducts = catalog
    .filter((product) => orderMap.has(product.handle))
    .sort((left, right) => orderMap.get(left.handle) - orderMap.get(right.handle))
    .map((product) => {
      const price = minPrice(product);
      const compareAtPrice = minCompareAtPrice(product);
      const availability = availabilityState(product, lowStockThreshold);
      const productBadges = [];
      if (collectionContext.featured_handles.includes(product.handle)) {
        productBadges.push(badges.featured);
      }
      if (compareAtPrice > price) {
        productBadges.push(badges.sale);
      }
      if (availability.value === "low_stock") {
        productBadges.push(badges.low_stock);
      }
      return {
        ...product,
        price,
        compare_at_price: compareAtPrice,
        inventory_total: sumInventory(product),
        availability_state: availability.value,
        availability_label: availability.label,
        badges: productBadges
      };
    });

  const filters = collectionContext.filters.map((filter) => {
    const values = selectedProducts.map((product) => {
      if (filter.source === "availability") {
        return product.availability_label;
      }
      return product[filter.source];
    });
    const counts = new Map();
    values.forEach((value) => {
      counts.set(value, (counts.get(value) || 0) + 1);
    });
    const orderedValues = sortByConfiguredOrder(new Set(values), filter.order || []);
    return {
      id: filter.id,
      label: filter.label,
      options: orderedValues.map((value) => ({
        value,
        count: counts.get(value) || 0
      }))
    };
  });

  return {
    collection: collectionContext.collection,
    section: blueprint.collection_section,
    selected_sort: collectionContext.default_sort,
    sort_options: collectionContext.sort_options,
    filters,
    products: selectedProducts
  };
}

export function buildPredictiveSearchModel(inputs, collectionModel) {
  const { predictiveSearch, blueprint } = inputs;
  const catalogByHandle = new Map(collectionModel.products.map((product) => [product.handle, product]));
  return {
    query: predictiveSearch.query,
    section: blueprint.predictive_search_section,
    groups: [
      {
        id: "queries",
        label: "Suggestions",
        items: predictiveSearch.queries.map((query) => ({ text: query }))
      },
      {
        id: "collections",
        label: "Collections",
        items: predictiveSearch.collections
      },
      {
        id: "products",
        label: "Products",
        items: predictiveSearch.products
          .map((handle) => catalogByHandle.get(handle))
          .filter(Boolean)
      }
    ]
  };
}

export function buildReportModel(inputs, collectionModel, searchModel, qualityChecks) {
  return {
    collection_handle: collectionModel.collection.handle,
    rendered_product_count: collectionModel.products.length,
    visible_filters: collectionModel.filters,
    sort_options: collectionModel.sort_options,
    search_groups: searchModel.groups.map((group) => ({
      id: group.id,
      count: group.items.length
    })),
    product_cards: collectionModel.products.map((product) => ({
      handle: product.handle,
      title: product.title,
      availability: product.availability_label,
      badges: product.badges,
      price: product.price
    })),
    quality_checks: qualityChecks
  };
}
