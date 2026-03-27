'use client';

import { useCallback, useMemo, useState } from 'react';
import { CatalogCard } from './CatalogCard';

interface CatalogItem {
  id: string;
  name: string;
  price: number;
  category: string;
  rating: number;
  inStock: boolean;
}

interface Review {
  id: string;
  itemId: string;
  text: string;
  rating: number;
  author: string;
}

interface Props {
  items: CatalogItem[];
  reviews: Review[];
}

export function CatalogList({ items, reviews }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [filter, setFilter] = useState('');
  const [sortBy, setSortBy] = useState<'price' | 'rating'>('price');

  const reviewCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const review of reviews) {
      counts[review.itemId] = (counts[review.itemId] ?? 0) + 1;
    }
    return counts;
  }, [reviews]);

  const visibleItems = useMemo(() => {
    const normalizedFilter = filter.toLowerCase();
    return items
      .filter((item) => item.name.toLowerCase().includes(normalizedFilter))
      .filter((item) => item.inStock)
      .slice()
      .sort((left, right) => (sortBy === 'price' ? left.price - right.price : right.rating - left.rating));
  }, [items, filter, sortBy]);

  const handleSelect = useCallback((itemId: string) => {
    setSelected((current) => [...current, itemId]);
  }, []);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Search products..."
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          className="rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={sortBy}
          onChange={(event) => setSortBy(event.target.value as 'price' | 'rating')}
          className="rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-blue-500"
        >
          <option value="price">Sort by Price</option>
          <option value="rating">Sort by Rating</option>
        </select>
        <div data-testid="cart-count" className="ml-auto rounded-lg bg-blue-100 px-4 py-2 font-medium text-blue-800">
          Cart: {selected.length} items
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {visibleItems.map((item) => (
          <CatalogCard
            key={item.id}
            item={item}
            reviewCount={reviewCounts[item.id] ?? 0}
            onSelect={handleSelect}
            isSelected={selected.includes(item.id)}
            buttonTestId="add-to-cart-"
            actionLabel="Add to Cart"
            addedLabel="In Cart"
          />
        ))}
      </div>
    </div>
  );
}
