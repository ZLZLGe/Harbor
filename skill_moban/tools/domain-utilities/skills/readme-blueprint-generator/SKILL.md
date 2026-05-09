# README Generator Prompt

Generate a comprehensive README.md for this repository by analyzing the documentation files in the .github/copilot directory and the copilot-instructions.md file. Follow these steps:

1. Scan all the files in the .github/copilot folder, like:

  * Architecture
  * Code\_Exemplars
  * Coding\_Standards
  * Project\_Folder\_Structure
  * Technology\_Stack
  * Unit\_Tests
  * Workflow\_Analysis
2. Also review the copilot-instructions.md file in the .github folder
3. Create a README.md with the following sections:

## Project Name and Description

* Extract the project name and primary purpose from the documentation
* Include a concise description of what the project does

## Technology Stack

* List the primary technologies, languages, and frameworks used
* Include version information when available
* Source this information primarily from the Technology\_Stack file

## Project Architecture

* Provide a high-level overview of the architecture
* Consider including a simple diagram if described in the documentation
* Source from the Architecture file

## Getting Started

* Include installation instructions based on the technology stack
* Add setup and configuration steps
* Include any prerequisites

## Project Structure

* Brief overview of the folder organization
* Source from Project\_Folder\_Structure file

## Key Features

* List main functionality and features of the project
* Extract from various documentation files

## Development Workflow

* Summarize the development process
* Include information about branching strategy if available
* Source from Workflow\_Analysis file

## Coding Standards

* Summarize key coding standards and conventions
* Source from the Coding\_Standards file

## Testing

* Explain testing approach and tools
* Source from Unit\_Tests file

## Contributing

* Guidelines for contributing to the project
* Reference any code exemplars for guidance
* Source from Code\_Exemplars and copilot-instructions

## License

* Include license information if available

Format the README with proper Markdown, including:

* Clear headings and subheadings
* Code blocks where appropriate
* Lists for better readability
* Links to other documentation files
* Badges for build status, version, etc. if information is available

Keep the README concise yet informative, focusing on what new developers or users would need to know about the project.
