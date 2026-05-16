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
  const values = product.variants
    .map((variant) => Number(variant.compare_at_price || 0))
    .filter((value) => value > 0);
  return values.length > 0 ? Math.min(...values) : 0;
}

function availabilityState(product, lowStockThreshold) {
  const total = sumInventory(product);
  if (total <= 0) {
    return { value: "out_of_stock", label: "Sold out" };
  }
  if (total <= lowStockThreshold) {
    return { value: "in_stock", label: "Low stock" };
  }
  return { value: "in_stock", label: "In stock" };
}

function filterValue(product, source) {
  if (source === "product_type") {
    return product.product_type;
  }
  if (source === "material") {
    return product.material;
  }
  if (source === "color") {
    return product.color;
  }
  return product.availability_label;
}

function sortValues(values, order) {
  const ranking = new Map(order.map((value, index) => [value, index]));
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
  const featuredOrder = new Map(collectionContext.featured_handles.map((handle, index) => [handle, index]));
  const orderMap = new Map(collectionContext.product_order.map((handle, index) => [handle, index]));
  const lowStockThreshold = Number(collectionContext.low_stock_threshold);

  const products = catalog
    .filter((product) => orderMap.has(product.handle))
    .map((product) => {
      const availability = availabilityState(product, lowStockThreshold);
      const badges = [];

      if (featuredOrder.has(product.handle)) {
        badges.push(collectionContext.badge_labels.featured);
      }
      if (availability.label === "Low stock") {
        badges.push(collectionContext.badge_labels.low_stock);
      }
      return {
        handle: product.handle,
        title: product.title,
        vendor: product.vendor,
        product_type: product.product_type,
        material: product.material,
        color: product.color,
        price: minPrice(product).toFixed(2),
        compare_at_price: minCompareAtPrice(product).toFixed(2),
        availability: availability.value,
        availability_label: availability.label,
        image: product.featured_image,
        image_alt: product.featured_image_alt,
        badges,
        sort_key: [
          featuredOrder.has(product.handle) ? 0 : 1,
          featuredOrder.get(product.handle) ?? Number.MAX_SAFE_INTEGER,
          orderMap.get(product.handle) ?? Number.MAX_SAFE_INTEGER
        ]
      };
    })
    .sort((left, right) => {
      for (let index = 0; index < left.sort_key.length; index += 1) {
        if (left.sort_key[index] !== right.sort_key[index]) {
          return left.sort_key[index] - right.sort_key[index];
        }
      }
      return 0;
    });

  const filters = collectionContext.filters.map((filter) => {
    const counts = new Map();
    for (const product of products) {
      const value = filterValue(product, filter.source);
      counts.set(value, (counts.get(value) || 0) + 1);
    }

    const values = sortValues(counts.keys(), filter.order || []).map((value) => ({
      label: value,
      count: counts.get(value) || 0
    }));

    return {
      id: filter.id,
      label: filter.label,
      values,
      options: values
    };
  });

  return {
    collection: collectionContext.collection,
    section: blueprint.collection_section,
    selected_sort: collectionContext.default_sort,
    sort_options: collectionContext.sort_options.map((option) => ({
      ...option,
      selected: option.value === collectionContext.default_sort
    })),
    filters,
    products
  };
}

export function buildPredictiveSearchModel(inputs, collectionModel) {
  const { predictiveSearch, blueprint } = inputs;
  const productByHandle = new Map(collectionModel.products.map((product) => [product.handle, product]));

  return {
    query: predictiveSearch.query,
    section: blueprint.predictive_search_section,
    groups: [
      {
        key: "queries",
        label: "Suggestions",
        items: predictiveSearch.queries.map((text) => ({ text }))
      },
      {
        key: "collections",
        label: "Collections",
        items: predictiveSearch.collections.map((item) => ({
          handle: item.handle,
          title: item.title
        }))
      },
      {
        key: "products",
        label: "Products",
        items: predictiveSearch.products
          .map((handle) => productByHandle.get(handle))
          .filter(Boolean)
          .map((product) => ({
            handle: product.handle,
            title: product.title,
            price: product.price
          }))
      }
    ]
  };
}

export function buildReportModel(collectionModel, searchModel, qualityChecks) {
  return {
    collection_handle: collectionModel.collection.handle,
    rendered_product_count: collectionModel.products.length,
    visible_filters: collectionModel.filters.map((filter) => ({
      id: filter.id,
      label: filter.label,
      values: filter.values
    })),
    sort_options: collectionModel.sort_options.map((option) => ({
      value: option.value,
      label: option.label,
      selected: Boolean(option.selected)
    })),
    search_groups: searchModel.groups.map((group) => ({
      key: group.key,
      label: group.label,
      count: group.items.length
    })),
    product_cards: collectionModel.products.map((product) => ({
      handle: product.handle,
      title: product.title,
      availability: product.availability,
      badges: product.badges,
      price: product.price
    })),
    quality_checks: qualityChecks
  };
}
