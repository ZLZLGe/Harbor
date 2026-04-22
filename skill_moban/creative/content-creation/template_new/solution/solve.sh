#!/bin/bash
set -euo pipefail

SOLUTION_DIR="/solution"

cp "$SOLUTION_DIR/fixed_blog_post.md" /root/blog_post.md
cp "$SOLUTION_DIR/fixed_linkedin_post.md" /root/linkedin_post.md
cp "$SOLUTION_DIR/fixed_newsletter.json" /root/newsletter.json
cp "$SOLUTION_DIR/fixed_seo_meta.json" /root/seo_meta.json

python /root/build_bundle.py
