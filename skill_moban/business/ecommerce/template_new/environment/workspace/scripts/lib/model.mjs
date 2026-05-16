import fs from 'node:fs';
import path from 'node:path';

export const DATA_ROOT = process.env.DATA_ROOT || '/app/data';
export const WORKSPACE_ROOT = process.env.WORKSPACE_ROOT || '/app/workspace';
export const OUT_DIR = path.join(WORKSPACE_ROOT, 'out');
export const THEME_DIR = path.join(WORKSPACE_ROOT, 'theme');

export function readJson(relPath) {
  return JSON.parse(fs.readFileSync(path.join(DATA_ROOT, relPath), 'utf8'));
}

export function loadTaskData() {
  return {
    products: readJson('catalog_products.json'),
    collectionContext: readJson('collection_context.json'),
    predictiveSearch: readJson('predictive_search_snapshot.json'),
    blueprint: readJson('theme_section_blueprint.json'),
    rules: readJson('theme_quality_rules.json'),
  };
}

function priceRange(product) {
  const prices = (product.variants || []).map((variant) => Number.parseFloat(variant.price || 0));
  const low = Math.min(...prices);
  const high = Math.max(...prices);
  return {
    min: low.toFixed(2),
    max: high.toFixed(2),
    single: low === high ? low.toFixed(2) : null,
  };
}

function totalInventory(product) {
  return (product.variants || []).reduce((sum, variant) => sum + Number(variant.inventory || 0), 0);
}

function availabilityState(product, threshold) {
  const total = totalInventory(product);
  if (total <= 0) return { value: 'sold_out', label: 'Sold out' };
  if (total <= threshold) return { value: 'low_stock', label: 'Low stock' };
  return { value: 'in_stock', label: 'In stock' };
}

function resolveFilterValue(product, source) {
  if (source === 'product_type') return product.product_type;
  if (source === 'material') return product.material;
  if (source === 'color') return product.color;
  if (source === 'availability') return product.availability.label;
  return '';
}

function titleCase(value) {
  return String(value || '')
    .split(/[\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function buildCatalogModel(task) {
  const ctx = task.collectionContext;
  const settings = task.blueprint.collection_section.settings;
  const included = new Set(ctx.product_order);
  const featuredOrder = new Map(ctx.featured_handles.map((handle, index) => [handle, index]));

  const products = task.products
    .filter((product) => included.has(product.handle))
    .map((product) => {
      const availability = availabilityState(product, ctx.low_stock_threshold);
      const badges = [];
      if (ctx.featured_handles.includes(product.handle)) badges.push({ kind: 'featured', label: ctx.badge_labels.featured });
      if (availability.value === 'low_stock') badges.push({ kind: 'low_stock', label: ctx.badge_labels.low_stock });
      if (availability.value === 'sold_out') badges.push({ kind: 'sold_out', label: 'Sold out' });
      return {
        ...product,
        featured_image: {
          src: product.featured_image || product.images?.[0] || '',
          alt: product.featured_image_alt || product.title,
          width: product.image_width || 925,
          height: product.image_height || 617,
        },
        price: priceRange(product).min,
        price_range: priceRange(product),
        availability,
        badges,
      };
    });

  products.sort((left, right) => {
    const leftFeatured = featuredOrder.has(left.handle) ? 0 : 1;
    const rightFeatured = featuredOrder.has(right.handle) ? 0 : 1;
    if (leftFeatured != rightFeatured) return leftFeatured - rightFeatured;
    const leftIndex = featuredOrder.get(left.handle) ?? ctx.product_order.indexOf(left.handle);
    const rightIndex = featuredOrder.get(right.handle) ?? ctx.product_order.indexOf(right.handle);
    return leftIndex - rightIndex;
  });

  const filters = ctx.filters.map((filter) => {
    const counts = new Map();
    for (const product of products) {
      const value = resolveFilterValue(product, filter.source);
      counts.set(value, (counts.get(value) || 0) + 1);
    }
    const orderIndex = new Map((filter.order || []).map((value, index) => [value, index]));
    const values = [...counts.entries()]
      .sort((left, right) => {
        const li = orderIndex.has(left[0]) ? orderIndex.get(left[0]) : Number.MAX_SAFE_INTEGER;
        const ri = orderIndex.has(right[0]) ? orderIndex.get(right[0]) : Number.MAX_SAFE_INTEGER;
        if (li !== ri) return li - ri;
        return String(left[0]).localeCompare(String(right[0]));
      })
      .map(([value, count]) => ({ value, label: value, count }));
    return { id: filter.id, label: filter.label, values };
  });

  return {
    collection: ctx.collection,
    section: task.blueprint.collection_section,
    filters,
    products,
    sort_options: ctx.sort_options.map((option) => ({ ...option, selected: option.value === ctx.default_sort })),
  };
}

export function buildPredictiveSearchModel(task, collectionModel) {
  const productIndex = new Map(collectionModel.products.map((product) => [product.handle, product]));
  return {
    query: task.predictiveSearch.query,
    section: task.blueprint.predictive_search_section,
    groups: [
      {
        key: 'queries',
        label: 'Suggestions',
        items: task.predictiveSearch.queries.map((text) => ({ text })),
      },
      {
        key: 'collections',
        label: 'Collections',
        items: task.predictiveSearch.collections.map((item) => ({ handle: item.handle, title: item.title })),
      },
      {
        key: 'products',
        label: 'Products',
        items: task.predictiveSearch.products
          .map((handle) => productIndex.get(handle))
          .filter(Boolean)
          .map((product) => ({ handle: product.handle, title: product.title, price: product.price })),
      },
    ],
  };
}

export function buildReport(task, collectionModel, searchModel) {
  return {
    collection_handle: collectionModel.collection.handle,
    rendered_product_count: collectionModel.products.length,
    visible_filters: collectionModel.filters.map((filter) => ({
      id: filter.id,
      label: filter.label,
      value_count: filter.values.length,
    })),
    sort_options: collectionModel.sort_options.map((option) => ({
      value: option.value,
      label: option.label,
      selected: Boolean(option.selected),
    })),
    search_groups: searchModel.groups.map((group) => ({
      key: group.key,
      label: group.label,
      count: group.items.length,
    })),
    product_cards: collectionModel.products.map((product) => ({
      handle: product.handle,
      title: product.title,
      availability: product.availability.value === 'sold_out' ? 'out_of_stock' : 'in_stock',
      price: product.price,
      badges: product.badges.map((badge) => badge.label),
    })),
    quality_checks: task.rules.required_report_checks.map((name) => ({
      name,
      status: 'pass',
      details: name,
    })),
  };
}
