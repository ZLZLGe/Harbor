# Transfer: Sparse Social Graph Recommender

In `/root/workspace/` there is a baseline script `social_graph_baseline.py` and a deterministic fixture generator `graph_fixture.py`.

The baseline builds a friendship recommender by materializing a dense adjacency matrix. That approach preserves the recommendation semantics, but it uses too much memory once the graph gets large. You need to write a replacement at `/root/workspace/graph_recommender_solution.py`.

Your script must support this command line interface:

```bash
python /root/workspace/graph_recommender_solution.py \
  --edges /path/to/friendships.csv \
  --targets /path/to/targets.json \
  --output /path/to/recommendations.json
```

Input files:

- `--edges` is a CSV file with header `user_id,friend_id`.
- Each CSV row represents one undirected friendship and appears exactly once.
- `user_id` and `friend_id` are integer user IDs in the inclusive range `0 .. num_users - 1`.
- `--targets` is a JSON object with this structure:

```json
{
  "num_users": 8,
  "top_n": 3,
  "target_user_ids": [0, 3, 6]
}
```

Recommendation semantics:

1. For each requested target user, consider every user who is:
   - not the target user, and
   - not already a direct friend of the target user.
2. The candidate score is the number of mutual friends shared with the target user.
3. Keep only candidates with score greater than zero.
4. Rank candidates by:
   - `mutual_friend_count` descending
   - `candidate_user_id` ascending
5. Return at most `top_n` candidates per target user.

Output contract:

1. Write a JSON object to `--output` with this exact top-level structure:

```json
{
  "graph": {
    "num_users": 0,
    "num_friendships": 0,
    "top_n": 0
  },
  "recommendations": [
    {
      "user_id": 0,
      "recommendations": [
        {
          "candidate_user_id": 4,
          "mutual_friend_count": 2
        }
      ]
    }
  ]
}
```

2. `graph.num_users` must equal `targets.json["num_users"]`.
3. `graph.num_friendships` must equal the number of CSV rows in `--edges`.
4. `graph.top_n` must equal `targets.json["top_n"]`.
5. The `recommendations` array must follow the same target order as `target_user_ids`.
6. The result must match the baseline semantics on the provided sample input and on verifier-generated fixtures.
7. On the large verifier fixture, peak RSS must stay at or below `180 MB`.
8. You may use `/tmp` for temporary files if needed, but the only required deliverable is `/root/workspace/graph_recommender_solution.py`.

Available assets:

- `/root/workspace/social_graph_baseline.py`
- `/root/workspace/graph_fixture.py`
- `/root/workspace/sample_friendships.csv`
- `/root/workspace/sample_targets.json`

The verifier will run your script on multiple friendship graphs and check both correctness and memory usage.
