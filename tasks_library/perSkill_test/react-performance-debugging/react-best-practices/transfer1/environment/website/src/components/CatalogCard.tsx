'use client';

interface CatalogItem {
  id: string;
  name: string;
  price: number;
  category: string;
  rating: number;
  inStock: boolean;
}

interface Props {
  item: CatalogItem;
  reviewCount: number;
  onSelect: (id: string) => void;
  isSelected: boolean;
  buttonTestId: string;
  actionLabel: string;
  addedLabel: string;
}

export function CatalogCard({ item, reviewCount, onSelect, isSelected, buttonTestId, actionLabel, addedLabel }: Props) {
  performance.mark(`CatalogCard-render-${item.id}`);

  return (
    <article className="overflow-hidden rounded-xl bg-white shadow-md transition-shadow hover:shadow-lg">
      <div className="flex h-40 items-center justify-center bg-gradient-to-br from-gray-100 to-gray-200">
        <span className="text-5xl">◈</span>
      </div>
      <div className="p-4">
        <div className="mb-2 flex items-start justify-between gap-3">
          <h3 className="text-lg font-semibold text-gray-900">{item.name}</h3>
          <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">{item.category}</span>
        </div>
        <div className="mb-2 flex items-center gap-1">
          {Array.from({ length: 5 }).map((_, index) => (
            <span key={index} className={index < item.rating ? 'text-yellow-400' : 'text-gray-300'}>
              ★
            </span>
          ))}
          <span className="ml-1 text-sm text-gray-500">({reviewCount})</span>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-2xl font-bold text-gray-900">${item.price.toFixed(2)}</span>
          <button
            data-testid={`${buttonTestId}${item.id}`}
            onClick={() => onSelect(item.id)}
            disabled={isSelected}
            className={`rounded-lg px-4 py-2 font-medium transition-colors ${
              isSelected
                ? 'cursor-not-allowed bg-gray-200 text-gray-500'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isSelected ? addedLabel : actionLabel}
          </button>
        </div>
      </div>
    </article>
  );
}
