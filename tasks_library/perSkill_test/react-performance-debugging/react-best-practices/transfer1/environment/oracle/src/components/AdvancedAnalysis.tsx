'use client';

import sortBy from 'lodash/sortBy';
import { mean, median, quantileSeq, std, variance } from 'mathjs';

interface CatalogItem {
  id: string;
  name: string;
  price: number;
  category: string;
  rating: number;
  reviews: number;
  inStock: boolean;
}

export default function AdvancedAnalysis({ items, heading }: { items: CatalogItem[]; heading?: string }) {
  const prices = items.map((item) => item.price);
  const ratings = items.map((item) => item.rating);
  const reviews = items.map((item) => item.reviews);

  const priceStats = {
    mean: mean(prices),
    median: median(prices),
    std: std(prices),
    variance: variance(prices),
    q1: quantileSeq(prices, 0.25),
    q3: quantileSeq(prices, 0.75),
  };

  const ratingStats = {
    mean: mean(ratings),
    median: median(ratings),
    std: std(ratings),
  };

  const reviewStats = {
    mean: mean(reviews),
    median: median(reviews),
    std: std(reviews),
  };

  const valueScores = sortBy(
    items.map((item) => ({ name: item.name, score: (item.rating / item.price) * 100 })),
    'score',
  ).reverse();

  return (
    <section data-testid="advanced-content" className="rounded-xl bg-white p-6 shadow-md">
      <h2 className="mb-4 text-xl font-bold">{heading ?? 'Advanced Analysis'}</h2>
      <div className="grid grid-cols-3 gap-6">
        <div>
          <h3 className="mb-3 font-semibold text-gray-700">Price Distribution</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>Mean:</span><span className="font-mono">${Number(priceStats.mean).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Median:</span><span className="font-mono">${Number(priceStats.median).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Std Dev:</span><span className="font-mono">${Number(priceStats.std).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Variance:</span><span className="font-mono">{Number(priceStats.variance).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Q1:</span><span className="font-mono">${Number(priceStats.q1).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Q3:</span><span className="font-mono">${Number(priceStats.q3).toFixed(2)}</span></div>
          </div>
        </div>
        <div>
          <h3 className="mb-3 font-semibold text-gray-700">Rating Analysis</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>Mean:</span><span className="font-mono">{Number(ratingStats.mean).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Median:</span><span className="font-mono">{Number(ratingStats.median).toFixed(2)}</span></div>
            <div className="flex justify-between"><span>Std Dev:</span><span className="font-mono">{Number(ratingStats.std).toFixed(3)}</span></div>
          </div>
        </div>
        <div>
          <h3 className="mb-3 font-semibold text-gray-700">Demand Signals</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span>Mean:</span><span className="font-mono">{Number(reviewStats.mean).toFixed(0)}</span></div>
            <div className="flex justify-between"><span>Median:</span><span className="font-mono">{Number(reviewStats.median).toFixed(0)}</span></div>
            <div className="flex justify-between"><span>Std Dev:</span><span className="font-mono">{Number(reviewStats.std).toFixed(0)}</span></div>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h3 className="mb-3 font-semibold text-gray-700">Value Ranking</h3>
        <div className="space-y-2">
          {valueScores.map((entry, index) => (
            <div key={entry.name} className="flex items-center gap-3">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-600 text-sm text-white">
                {index + 1}
              </span>
              <span className="flex-1">{entry.name}</span>
              <span className="font-mono text-blue-600">{entry.score.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
