'use client';

import { useState } from 'react';
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

  const visibleItems = items
    .filter((item) => item.name.toLowerCase().includes(filter.toLowerCase()))
    .filter((item) => item.inStock)
    .sort((left, right) => (sortBy === 'price' ? left.price - right.price : right.rating - left.rating));

  const handleSelect = (itemId: string) => {
    setSelected((current) => [...current, itemId]);
  };

  const getReviewCount = (itemId: string) => {
    return reviews.filter((review) => review.itemId === itemId).length;
  };

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-4">
        <input
          type="text"
          placeholder="Search courses..."
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
        <div data-testid="saved-count" className="ml-auto rounded-lg bg-blue-100 px-4 py-2 font-medium text-blue-800">
          Saved: {selected.length} courses
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        {visibleItems.map((item) => (
          <CatalogCard
            key={item.id}
            item={item}
            reviewCount={getReviewCount(item.id)}
            onSelect={handleSelect}
            isSelected={selected.includes(item.id)}
            buttonTestId="save-course-"
            actionLabel="Save to Plan"
            addedLabel="Saved"
          />
        ))}
      </div>
    </div>
  );
}
