You are given a product launch content pack and need to turn it into a set of publish-ready deliverables for different channels.

The source materials are in:
- `/root/launch_brief.md`
- `/root/fact_sheet.json`
- `/root/voice_guide.md`
- `/root/channel_requirements.md`
- `/root/keyword_plan.json`
- `/root/source_notes.md`

Your task is to create the following files:

1. `/root/blog_post.md`
- Write a publish-ready blog post in Markdown
- The blog post should clearly explain the product launch
- It should follow the brand voice guide
- It should include the main launch facts from the fact sheet
- It should use the SEO keyword plan naturally
- It should end with a clear CTA

2. `/root/linkedin_post.md`
- Write a LinkedIn post for the same launch
- It should keep the same core facts as the blog post
- But it must be adapted to LinkedIn style rather than copied from the blog post
- Keep it concise and channel-appropriate

3. `/root/newsletter.json`
- Create a valid JSON file with the following fields:
```json
{
  "subject": "...",
  "preview_text": "...",
  "body_markdown": "...",
  "cta_label": "...",
  "cta_url": "..."
}
```
- The newsletter should match the same launch facts
- It should follow the channel requirements
- The body should read like a real newsletter section, not like a pasted blog post

4. `/root/seo_meta.json`
- Create a valid JSON file with the following fields:
```json
{
  "slug": "...",
  "title": "...",
  "description": "...",
  "primary_keyword": "...",
  "secondary_keywords": ["...", "...", "..."]
}
```
- The SEO metadata should match the keyword plan
- It should also align with the blog post content

5. Run the bundle packaging script
- Run `python /root/build_bundle.py`
- Save the generated bundle summary to `/root/publish_bundle.json`

Requirements:
- Keep all outputs factually consistent with the provided materials
- Do not invent product capabilities, pricing, language support, or plan availability not stated in the inputs
- Do not make the LinkedIn post and newsletter body simple copies of the blog post
- Follow the voice guide and channel requirements
- All output files must be complete and valid

Notes:
- You may use any tools you want
- The final outputs should be saved exactly to the required paths
- The evaluator will check factual accuracy, file validity, structural completeness, keyword alignment, and cross-channel consistency
