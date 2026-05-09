# Markdown to HTML Conversion

Expert skill for converting Markdown documents to HTML using the marked.js library, or writing data conversion scripts; in this case scripts similar to [markedJS/marked](https://github.com/markedjs/marked) repository. For custom scripts knowledge is not confined to `marked.js`, but data conversion methods are utilized from tools like [pandoc](https://github.com/jgm/pandoc) and [gomarkdown/markdown](https://github.com/gomarkdown/markdown) for data conversion; [jekyll/jekyll](https://github.com/jekyll/jekyll) and [gohugoio/hugo](https://github.com/gohugoio/hugo) for templating systems.

The conversion script or tool should handle single files, batch conversions, and advanced configurations.

## When to Use This Skill

* User asks to "convert markdown to html" or "transform md files"
* User wants to "render markdown" as HTML output
* User needs to generate HTML documentation from .md files
* User is building static sites from Markdown content
* User is building template system that converts markdown to html
* User is working on a tool, widget, or custom template for an existing templating system
* User wants to preview Markdown as rendered HTML

## Converting Markdown to HTML

### Essential Basic Conversions

For more see [basic-markdown-to-html.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/basic-markdown-to-html.md)

    ```markdown
    # Level 1
    ## Level 2

    One sentence with a [link](https://example.com), and a HTML snippet like `

paragraph tag

`.

    - `ul` list item 1
    - `ul` list item 2

    1. `ol` list item 1
    2. `ol` list item 1

    | Table Item | Description |
    | One | One is the spelling of the number `1`. |
    | Two | Two is the spelling of the number `2`. |

    ```js
    var one = 1;
    var two = 2;

    function simpleMath(x, y) {
     return x + y;
    }
    console.log(simpleMath(one, two));
    ```
    ```

    ```html
    
# Level 1


    ## Level 2


    One sentence with a [link](https://example.com), and a HTML snippet like `<p>paragraph tag</p>`.

    
     * `ul` list item 1

     * `ul` list item 2

    
     * `ol` list item 1

     * `ol` list item 2
      
       
Table Item


       Description
      
       
One


       One is the spelling of the number `1`.
      
       
Two


       Two is the spelling of the number `2`.

    
     ```` var one = 1;
     var two = 2;

     function simpleMath(x, y) {
      return x + y;
     }
     console.log(simpleMath(one, two));
    
    ```
 ````

### Code Block Conversions


For more see [code-blocks-to-html.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/code-blocks-to-html.md)


    ```markdown
    your code here
    ```

    ```html
    
    your code here
    
    ```

    ```js
    console.log("Hello world");
    ```

    ```html
    
    console.log("Hello world");
    
    ```

    ```markdown
      ```

      ```
      visible backticks
      ```

      ```
    ```

    ```html
      
```

      ```

      visible backticks

      ```
      
    ```

```


### Collapsed Section Conversions


For more see [collapsed-sections-to-html.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/collapsed-sections-to-html.md)


    ```markdown
    
    More info

    ### Header inside

    - Lists
    - **Formatting**
    - Code blocks

        ```js
        console.log("Hello");
        ```

    
    ```

    ```html
    
    More info

    ### Header inside

    
     * Lists

     * **Formatting**

     * Code blocks

    
     `console.log("Hello");`

    
    ```


### Mathematical Expression Conversions


For more see [writing-mathematical-expressions-to-html.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/writing-mathematical-expressions-to-html.md)


    ```markdown
    This sentence uses `$` delimiters to show math inline: $\sqrt{3x-1}+(1+x)^2$
    ```

    ```html
    This sentence uses `$` delimiters to show math inline:
     
      3x−1
      +(1+x
      )2
    
    
    ```

    ```markdown
    **The Cauchy-Schwarz Inequality**\
    $$\left( \sum_{k=1}^n a_k b_k \right)^2 \leq \left( \sum_{k=1}^n a_k^2 \right) \left( \sum_{k=1}^n b_k^2 \right)$$
    ```

    ```html
    **The Cauchy-Schwarz Inequality**  
      
       
        (
         ∑
          k=1n
         
         ak
         bk
         )
        
        2
       
       ≤
       (
        ∑
         k=1
         n
        
        ak2
        )
       
       (
         ∑
          k=1
          n
         
         bk2
         )
      
     
    ```

### Table Conversions


For more see [tables-to-html.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/tables-to-html.md)


    ```markdown
    | First Header  | Second Header |
    | ------------- | ------------- |
    | Content Cell  | Content Cell  |
    | Content Cell  | Content Cell  |
    ```

    ```html
    
     
First Header

Second Header
     
      
Content Cell

Content Cell


      Content Cell

Content Cell
     
    
    ```

    ```markdown
    | Left-aligned | Center-aligned | Right-aligned |
    | :---         |     :---:      |          ---: |
    | git status   | git status     | git status    |
    | git diff     | git diff       | git diff      |
    ```

    ```html
       
        
Left-aligned


        Center-aligned


        Right-aligned
       
        
git status


        git status


        git status
       
        
git diff


        git diff


        git diff
      
    
    ```

## Working with [markedJS/marked](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/marked.md)


### Prerequisites


* Node.js installed (for CLI or programmatic usage)

* Install marked globally for CLI: `npm install -g marked`

* Or install locally: `npm install marked`


### Quick Conversion Methods


See [marked.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/marked.md) **Quick Conversion Methods**


### Step-by-Step Workflows


See [marked.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/marked.md) **Step-by-Step Workflows**


### CLI Configuration


### Using Config Files


Create `~/.marked.json` for persistent options:


```json
{
  "gfm": true,
  "breaks": true
}

```


Or use a custom config:


```bash
marked -i input.md -o output.html -c config.json

```


### CLI Options Reference


Option


Description


-i, --input 

Input Markdown file


-o, --output 

Output HTML file


-s, --string 

Parse string instead of file


-c, --config 

Use custom config file


`--gfm`


Enable GitHub Flavored Markdown


`--breaks`


Convert newlines to `  
`


`--help`


Show all options


### Security Warning


⚠️ **Marked does NOT sanitize output HTML.** For untrusted input, use a sanitizer:


```javascript
import { marked } from 'marked';
import DOMPurify from 'dompurify';

const unsafeHtml = marked.parse(untrustedMarkdown);
const safeHtml = DOMPurify.sanitize(unsafeHtml);

```


Recommended sanitizers:


* [DOMPurify](https://github.com/cure53/DOMPurify) (recommended)

* [sanitize-html](https://github.com/apostrophecms/sanitize-html)

* [js-xss](https://github.com/leizongmin/js-xss)


### Supported Markdown Flavors


| |                        |
| ------------------------ |
| Flavor                   |
| Support                  |
| |                        |
| Original Markdown        |
| 100%                     |
| |                        |
| CommonMark 0.31          |
| 98%                      |
| |                        |
| GitHub Flavored Markdown |
| 97%                      |


### Troubleshooting


| |                                                                         |
| ------------------------------------------------------------------------- |
| Issue                                                                     |
| Solution                                                                  |
| |                                                                         |
| Special characters at file start                                          |
| Strip zero-width chars: content.replace(/^[\u200B\u200C\u200D\uFEFF]/,"") |
| |                                                                         |
| Code blocks not highlighting                                              |
| Add a syntax highlighter like highlight.js                                |
| |                                                                         |
| Tables not rendering                                                      |
| Ensure gfm: true option is set                                            |
| |                                                                         |
| Line breaks ignored                                                       |
| Set breaks: true in options                                               |
| |                                                                         |
| XSS vulnerability concerns                                                |
| Use DOMPurify to sanitize output                                          |


## Working with [pandoc](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/pandoc.md)


### Prerequisites


* Pandoc installed (download from <https://pandoc.org/installing.html>)

* For PDF output: LaTeX installation (MacTeX on macOS, MiKTeX on Windows, texlive on Linux)

* Terminal/command prompt access


### Quick Conversion Methods


#### Method 1: CLI Basic Conversion


```bash
# Convert markdown to HTML
pandoc input.md -o output.html

# Convert with standalone document (includes header/footer)
pandoc input.md -s -o output.html

# Explicit format specification
pandoc input.md -f markdown -t html -s -o output.html

```


#### Method 2: Filter Mode (Interactive)


```bash
# Start pandoc as a filter
pandoc

# Type markdown, then Ctrl-D (Linux/macOS) or Ctrl-Z+Enter (Windows)
Hello *pandoc*!
# Output: Hello pandoc!

```


#### Method 3: Format Conversion


```bash
# HTML to Markdown
pandoc -f html -t markdown input.html -o output.md

# Markdown to LaTeX
pandoc input.md -s -o output.tex

# Markdown to PDF (requires LaTeX)
pandoc input.md -s -o output.pdf

# Markdown to Word
pandoc input.md -s -o output.docx

```


### CLI Configuration


Option


Description


-f, --from 

Input format (markdown, html, latex, etc.)


-t, --to 

Output format (html, latex, pdf, docx, etc.)


`-s, --standalone`


Produce standalone document with header/footer


-o, --output 

Output file (inferred from extension)


`--mathml`


Convert TeX math to MathML


`--metadata title="Title"`


Set document metadata


`--toc`


Include table of contents


--template 

Use custom template


`--help`


Show all options


### Security Warning


⚠️ **Pandoc processes input faithfully.** When converting untrusted markdown:


* Use `--sandbox` mode to disable external file access

* Validate input before processing

* Sanitize HTML output if displayed in browsers


```bash
# Run in sandbox mode for untrusted input
pandoc --sandbox input.md -o output.html

```


### Supported Markdown Flavors


| |                        |
| ------------------------ |
| Flavor                   |
| Support                  |
| |                        |
| Pandoc Markdown          |
| 100% (native)            |
| |                        |
| CommonMark               |
| Full (use -f commonmark) |
| |                        |
| GitHub Flavored Markdown |
| Full (use -f gfm)        |
| |                        |
| MultiMarkdown            |
| Partial                  |


### Troubleshooting


| |                                                |
| ------------------------------------------------ |
| Issue                                            |
| Solution                                         |
| |                                                |
| PDF generation fails                             |
| Install LaTeX (MacTeX, MiKTeX, or texlive)       |
| |                                                |
| Encoding issues on Windows                       |
| Run chcp 65001 before using pandoc               |
| |                                                |
| Missing standalone headers                       |
| Add -s flag for complete documents               |
| |                                                |
| Math not rendering                               |
| Use --mathml or --mathjax option                 |
| |                                                |
| Tables not rendering                             |
| Ensure proper table syntax with pipes and dashes |


## Working with [gomarkdown/markdown](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/gomarkdown.md)


### Prerequisites


* Go 1.18 or higher installed

* Install the library: `go get github.com/gomarkdown/markdown`

* For CLI tool: `go install github.com/gomarkdown/mdtohtml@latest`


### Quick Conversion Methods


#### Method 1: Simple Conversion (Go)


```go
package main

import (
    "fmt"
    "github.com/gomarkdown/markdown"
)

func main() {
    md := []byte("# Hello World\n\nThis is **bold** text.")
    html := markdown.ToHTML(md, nil, nil)
    fmt.Println(string(html))
}

```


#### Method 2: CLI Tool


```bash
# Install mdtohtml
go install github.com/gomarkdown/mdtohtml@latest

# Convert file
mdtohtml input.md output.html

# Convert file (output to stdout)
mdtohtml input.md

```


#### Method 3: Custom Parser and Renderer


```go
package main

import (
    "github.com/gomarkdown/markdown"
    "github.com/gomarkdown/markdown/html"
    "github.com/gomarkdown/markdown/parser"
)

func mdToHTML(md []byte) []byte {
    // Create parser with extensions
    extensions := parser.CommonExtensions | parser.AutoHeadingIDs | parser.NoEmptyLineBeforeBlock
    p := parser.NewWithExtensions(extensions)
    doc := p.Parse(md)

    // Create HTML renderer with extensions
    htmlFlags := html.CommonFlags | html.HrefTargetBlank
    opts := html.RendererOptions{Flags: htmlFlags}
    renderer := html.NewRenderer(opts)

    return markdown.Render(doc, renderer)
}

```


### CLI Configuration


The `mdtohtml` CLI tool has minimal options:


```bash
mdtohtml input-file [output-file]

```


For advanced configuration, use the Go library programmatically with parser and renderer options:


| |                                                   |
| --------------------------------------------------- |
| Parser Extension                                    |
| Description                                         |
| |                                                   |
| parser.CommonExtensions                             |
| Tables, fenced code, autolinks, strikethrough, etc. |
| |                                                   |
| parser.AutoHeadingIDs                               |
| Generate IDs for headings                           |
| |                                                   |
| parser.NoEmptyLineBeforeBlock                       |
| No blank line needed before blocks                  |
| |                                                   |
| parser.MathJax                                      |
| MathJax support for LaTeX math                      |


| |                            |
| ---------------------------- |
| HTML Flag                    |
| Description                  |
| |                            |
| html.CommonFlags             |
| Common HTML output flags     |
| |                            |
| html.HrefTargetBlank         |
| Add target="_blank" to links |
| |                            |
| html.CompletePage            |
| Generate complete HTML page  |
| |                            |
| html.UseXHTML                |
| Generate XHTML output        |


### Security Warning


⚠️ **gomarkdown does NOT sanitize output HTML.** For untrusted input, use Bluemonday:


```go
import (
    "github.com/microcosm-cc/bluemonday"
    "github.com/gomarkdown/markdown"
)

maybeUnsafeHTML := markdown.ToHTML(md, nil, nil)
html := bluemonday.UGCPolicy().SanitizeBytes(maybeUnsafeHTML)

```


Recommended sanitizer: [Bluemonday](https://github.com/microcosm-cc/bluemonday)


### Supported Markdown Flavors


| |                                         |
| ----------------------------------------- |
| Flavor                                    |
| Support                                   |
| |                                         |
| Original Markdown                         |
| 100%                                      |
| |                                         |
| CommonMark                                |
| High (with extensions)                    |
| |                                         |
| GitHub Flavored Markdown                  |
| High (tables, fenced code, strikethrough) |
| |                                         |
| MathJax/LaTeX Math                        |
| Supported via extension                   |
| |                                         |
| Mmark                                     |
| Supported                                 |


### Troubleshooting


| |                                             |
| --------------------------------------------- |
| Issue                                         |
| Solution                                      |
| |                                             |
| Windows/Mac newlines not parsed               |
| Use parser.NormalizeNewlines(input)           |
| |                                             |
| Tables not rendering                          |
| Enable parser.Tables extension                |
| |                                             |
| Code blocks without highlighting              |
| Integrate with syntax highlighter like Chroma |
| |                                             |
| Math not rendering                            |
| Enable parser.MathJax extension               |
| |                                             |
| XSS vulnerabilities                           |
| Use Bluemonday to sanitize output             |


## Working with [jekyll](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/jekyll.md)


### Prerequisites


* Ruby version 2.7.0 or higher

* RubyGems

* GCC and Make (for native extensions)

* Install Jekyll and Bundler: `gem install jekyll bundler`


### Quick Conversion Methods


#### Method 1: Create New Site


```bash
# Create a new Jekyll site
jekyll new myblog

# Change to site directory
cd myblog

# Build and serve locally
bundle exec jekyll serve

# Access at http://localhost:4000

```


#### Method 2: Build Static Site


```bash
# Build site to _site directory
bundle exec jekyll build

# Build with production environment
JEKYLL_ENV=production bundle exec jekyll build

```


#### Method 3: Live Reload Development


```bash
# Serve with live reload
bundle exec jekyll serve --livereload

# Serve with drafts
bundle exec jekyll serve --drafts

```


### CLI Configuration


Command


Description


jekyll new 

Create new Jekyll site


`jekyll build`


Build site to `_site` directory


`jekyll serve`


Build and serve locally


`jekyll clean`


Remove generated files


`jekyll doctor`


Check for configuration issues


Serve Options


Description


`--livereload`


Reload browser on changes


`--drafts`


Include draft posts


--port 

Set server port (default: 4000)


--host 

Set server host (default: localhost)


--baseurl 

Set base URL


### Security Warning


⚠️ **Jekyll security considerations:**


* Avoid using `safe: false` in production

* Use `exclude` in `_config.yml` to prevent sensitive files from being published

* Sanitize user-generated content if accepting external input

* Keep Jekyll and plugins updated


```yaml
# _config.yml security settings
exclude:
  - Gemfile
  - Gemfile.lock
  - node_modules
  - vendor

```


### Supported Markdown Flavors


| |                                      |
| -------------------------------------- |
| Flavor                                 |
| Support                                |
| |                                      |
| Kramdown (default)                     |
| 100%                                   |
| |                                      |
| CommonMark                             |
| Via plugin (jekyll-commonmark)         |
| |                                      |
| GitHub Flavored Markdown               |
| Via plugin (jekyll-commonmark-ghpages) |
| |                                      |
| RedCarpet                              |
| Via plugin (deprecated)                |


Configure markdown processor in `_config.yml`:


```yaml
markdown: kramdown
kramdown:
  input: GFM
  syntax_highlighter: rouge

```


### Troubleshooting


| |                                |
| -------------------------------- |
| Issue                            |
| Solution                         |
| |                                |
| Ruby 3.0+ fails to serve         |
| Run bundle add webrick           |
| |                                |
| Gem dependency errors            |
| Run bundle install               |
| |                                |
| Slow builds                      |
| Use --incremental flag           |
| |                                |
| Liquid syntax errors             |
| Check for unescaped { in content |
| |                                |
| Plugin not loading               |
| Add to _config.yml plugins list  |


## Working with [hugo](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/hugo.md)


### Prerequisites


* Hugo installed (download from <https://gohugo.io/installation/>)

* Git (recommended for themes and modules)

* Go (optional, for Hugo Modules)


### Quick Conversion Methods


#### Method 1: Create New Site


```bash
# Create a new Hugo site
hugo new site mysite

# Change to site directory
cd mysite

# Add a theme
git init
git submodule add https://github.com/theNewDynamic/gohugo-theme-ananke themes/ananke
echo "theme = 'ananke'" >> hugo.toml

# Create content
hugo new content posts/my-first-post.md

# Start development server
hugo server -D

```


#### Method 2: Build Static Site


```bash
# Build site to public directory
hugo

# Build with minification
hugo --minify

# Build for specific environment
hugo --environment production

```


#### Method 3: Development Server


```bash
# Start server with drafts
hugo server -D

# Start with live reload and bind to all interfaces
hugo server --bind 0.0.0.0 --baseURL http://localhost:1313/

# Start with specific port
hugo server --port 8080

```


### CLI Configuration


Command


Description


hugo new site 

Create new Hugo site


hugo new content 

Create new content file


`hugo`


Build site to `public` directory


`hugo server`


Start development server


`hugo mod init`


Initialize Hugo Modules


Build Options


Description


`-D, --buildDrafts`


Include draft content


`-E, --buildExpired`


Include expired content


`-F, --buildFuture`


Include future-dated content


`--minify`


Minify output


`--gc`


Run garbage collection after build


-d, --destination 

Output directory


Server Options


Description


--bind 

Interface to bind to


-p, --port 

Port number (default: 1313)


--liveReloadPort 

Live reload port


`--disableLiveReload`


Disable live reload


`--navigateToChanged`


Navigate to changed content


### Security Warning


⚠️ **Hugo security considerations:**


* Configure security policy in `hugo.toml` for external commands

* Use `--enableGitInfo` carefully with public repositories

* Validate shortcode parameters for user-generated content


```toml
# hugo.toml security settings
[security]
  enableInlineShortcodes = false
  [security.exec]
    allow = ['^go$', '^npx$', '^postcss$']
  [security.funcs]
    getenv = ['^HUGO_', '^CI$']
  [security.http]
    methods = ['(?i)GET|POST']
    urls = ['.*']

```


### Supported Markdown Flavors


| |                                       |
| --------------------------------------- |
| Flavor                                  |
| Support                                 |
| |                                       |
| Goldmark (default)                      |
| 100% (CommonMark compliant)             |
| |                                       |
| GitHub Flavored Markdown                |
| Full (tables, strikethrough, autolinks) |
| |                                       |
| CommonMark                              |
| 100%                                    |
| |                                       |
| Blackfriday (legacy)                    |
| Deprecated, not recommended             |


Configure markdown in `hugo.toml`:


```toml
[markup]
  [markup.goldmark]
    [markup.goldmark.extensions]
      definitionList = true
      footnote = true
      linkify = true
      strikethrough = true
      table = true
      taskList = true
    [markup.goldmark.renderer]
      unsafe = false  # Set true to allow raw HTML

```


### Troubleshooting


| |                                             |
| --------------------------------------------- |
| Issue                                         |
| Solution                                      |
| |                                             |
| "Page not found" on paths                     |
| Check baseURL in config                       |
| |                                             |
| Theme not loading                             |
| Verify theme in themes/ or Hugo Modules       |
| |                                             |
| Slow builds                                   |
| Use --templateMetrics to identify bottlenecks |
| |                                             |
| Raw HTML not rendering                        |
| Set unsafe = true in goldmark config          |
| |                                             |
| Images not loading                            |
| Check static/ folder structure                |
| |                                             |
| Module errors                                 |
| Run hugo mod tidy                             |


## References


### Writing and Styling Markdown


* [basic-markdown.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/basic-markdown.md)

* [code-blocks.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/code-blocks.md)

* [collapsed-sections.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/collapsed-sections.md)

* [tables.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/tables.md)

* [writing-mathematical-expressions.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/writing-mathematical-expressions.md)

* Markdown Guide: <https://www.markdownguide.org/basic-syntax/>

* Styling Markdown: <https://github.com/sindresorhus/github-markdown-css>


### [markedJS/marked](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/marked.md)


* Official documentation: <https://marked.js.org/>

* Advanced options: <https://marked.js.org/using%5Fadvanced>

* Extensibility: <https://marked.js.org/using%5Fpro>

* GitHub repository: <https://github.com/markedjs/marked>


### [pandoc](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/pandoc.md)


* Getting started: <https://pandoc.org/getting-started.html>

* Official documentation: <https://pandoc.org/MANUAL.html>

* Extensibility: <https://pandoc.org/extras.html>

* GitHub repository: <https://github.com/jgm/pandoc>


### [gomarkdown/markdown](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/gomarkdown.md)


* Official documentation: <https://pkg.go.dev/github.com/gomarkdown/markdown>

* Advanced configuration: <https://pkg.go.dev/github.com/gomarkdown/markdown@v0.0.0-20250810172220-2e2c11897d1a/html>

* Markdown processing: <https://blog.kowalczyk.info/article/cxn3/advanced-markdown-processing-in-go.html>

* GitHub repository: <https://github.com/gomarkdown/markdown>


### [jekyll](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/jekyll.md)


* Official documentation: <https://jekyllrb.com/docs/>

* Configuration options: <https://jekyllrb.com/docs/configuration/options/>

* Plugins: <https://jekyllrb.com/docs/plugins/>

  * [Installation](https://jekyllrb.com/docs/plugins/installation/)

  * [Generators](https://jekyllrb.com/docs/plugins/generators/)

  * [Converters](https://jekyllrb.com/docs/plugins/converters/)

  * [Commands](https://jekyllrb.com/docs/plugins/commands/)

  * [Tags](https://jekyllrb.com/docs/plugins/tags/)

  * [Filters](https://jekyllrb.com/docs/plugins/filters/)

  * [Hooks](https://jekyllrb.com/docs/plugins/hooks/)

* GitHub repository: <https://github.com/jekyll/jekyll>


### [hugo](https://github.com/github/awesome-copilot/blob/HEAD/skills/markdown-to-html/references/hugo.md)


* Official documentation: <https://gohugo.io/documentation/>

* All Settings: <https://gohugo.io/configuration/all/>

* Editor Plugins: <https://gohugo.io/tools/editors/>

* GitHub repository: <https://github.com/gohugoio/hugo>
