You are preparing a cuisine coverage handout for a recruiting tour.

Input file in `/root/data/`:
1. `transfer3_matrix_request.json`

Use the bundled city restaurant lookup instead of memory.

Produce this file in `/root/`:
1. `transfer3_cuisine_matrix.csv`

Requirements:
1. Search restaurants separately for every requested city.
2. For each city and requested cuisine, find all restaurants whose cuisine list contains that cuisine substring, case-insensitively.
3. Produce one CSV row per `(city, requested_cuisine)` pair.
4. Preserve the city order from the request file, and within each city preserve the cuisine order from the request file.
5. Use this exact header row:
   - `city,requested_cuisine,match_count,cheapest_restaurant,cheapest_cost,highest_rated_restaurant,highest_rating`
6. `match_count` is the number of matching restaurants for that city and cuisine.
7. `cheapest_restaurant` must be selected by:
   - lowest `Average Cost`
   - then highest `Aggregate Rating`
   - then restaurant name alphabetically
8. `highest_rated_restaurant` must be selected by:
   - highest `Aggregate Rating`
   - then lowest `Average Cost`
   - then restaurant name alphabetically
9. Write numeric costs and ratings as plain decimal values.
