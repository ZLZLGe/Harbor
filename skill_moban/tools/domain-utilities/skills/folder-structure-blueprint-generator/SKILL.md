# Project Folder Structure Blueprint Generator

## Configuration Variables

${PROJECT\_TYPE="Auto-detect|.NET|Java|React|Angular|Python|Node.js|Flutter|Other"}

${INCLUDES\_MICROSERVICES="Auto-detect|true|false"}

${INCLUDES\_FRONTEND="Auto-detect|true|false"}

${IS\_MONOREPO="Auto-detect|true|false"}

${VISUALIZATION\_STYLE="ASCII|Markdown List|Table"}

${DEPTH\_LEVEL=1-5}

${INCLUDE\_FILE\_COUNTS=true|false}

${INCLUDE\_GENERATED\_FOLDERS=true|false}

${INCLUDE\_FILE\_PATTERNS=true|false}

${INCLUDE\_TEMPLATES=true|false}

## Generated Prompt

"Analyze the project's folder structure and create a comprehensive 'Project\_Folders\_Structure\_Blueprint.md' document that serves as a definitive guide for maintaining consistent code organization. Use the following approach:

### Initial Auto-detection Phase

${PROJECT\_TYPE == "Auto-detect" ? "Begin by scanning the folder structure for key files that identify the project type:

* Look for solution/project files (.sln, .csproj, .fsproj, .vbproj) to identify .NET projects
* Check for build files (pom.xml, build.gradle, settings.gradle) for Java projects
* Identify package.json with dependencies for JavaScript/TypeScript projects
* Look for specific framework files (angular.json, react-scripts entries, next.config.js)
* Check for Python project identifiers (requirements.txt, setup.py, pyproject.toml)
* Examine mobile app identifiers (pubspec.yaml, android/ios folders)
* Note all technology signatures found and their versions" : "Focus analysis on ${PROJECT\_TYPE} project structure"}

${IS\_MONOREPO == "Auto-detect" ? "Determine if this is a monorepo by looking for:

* Multiple distinct projects with their own configuration files
* Workspace configuration files (lerna.json, nx.json, turborepo.json, etc.)
* Cross-project references and shared dependency patterns
* Root-level orchestration scripts and configuration" : ""}

${INCLUDES\_MICROSERVICES == "Auto-detect" ? "Check for microservices architecture indicators:

* Multiple service directories with similar/repeated structures
* Service-specific Dockerfiles or deployment configurations
* Inter-service communication patterns (APIs, message brokers)
* Service registry or discovery configuration
* API gateway configuration files
* Shared libraries or utilities across services" : ""}

${INCLUDES\_FRONTEND == "Auto-detect" ? "Identify frontend components by looking for:

* Web asset directories (wwwroot, public, dist, static)
* UI framework files (components, modules, pages)
* Frontend build configuration (webpack, vite, rollup, etc.)
* Style sheet organization (CSS, SCSS, styled-components)
* Static asset organization (images, fonts, icons)" : ""}

### 1\. Structural Overview

Provide a high-level overview of the ${PROJECT\_TYPE == "Auto-detect" ? "detected project type(s)" : PROJECT\_TYPE} project's organization principles and folder structure:

* Document the overall architectural approach reflected in the folder structure
* Identify the main organizational principles (by feature, by layer, by domain, etc.)
* Note any structural patterns that repeat throughout the codebase
* Document the rationale behind the structure where it can be inferred

${IS\_MONOREPO == "Auto-detect" ? "If detected as a monorepo, explain how the monorepo is organized and the relationship between projects." : IS\_MONOREPO ? "Explain how the monorepo is organized and the relationship between projects." : ""}

${INCLUDES\_MICROSERVICES == "Auto-detect" ? "If microservices are detected, describe how they are structured and organized." : INCLUDES\_MICROSERVICES ? "Describe how the microservices are structured and organized." : ""}

### 2\. Directory Visualization

${VISUALIZATION\_STYLE == "ASCII" ? "Create an ASCII tree representation of the folder hierarchy to depth level ${DEPTH\_LEVEL}." : ""}

${VISUALIZATION\_STYLE == "Markdown List" ? "Use nested markdown lists to represent the folder hierarchy to depth level ${DEPTH\_LEVEL}." : ""}

${VISUALIZATION\_STYLE == "Table" ? "Create a table with columns for Path, Purpose, Content Types, and Conventions." : ""}

${INCLUDE\_GENERATED\_FOLDERS ? "Include all folders including generated ones." : "Exclude auto-generated folders like bin/, obj/, node\_modules/, etc."}

### 3\. Key Directory Analysis

Document each significant directory's purpose, contents, and patterns:

${PROJECT\_TYPE == "Auto-detect" ? "For each detected technology, analyze directory structures based on observed usage patterns:" : ""}

${(PROJECT\_TYPE == ".NET" || PROJECT\_TYPE == "Auto-detect") ? "#### .NET Project Structure (if detected)

* **Solution Organization**:

  * How projects are grouped and related
  * Solution folder organization patterns
  * Multi-targeting project patterns
* **Project Organization**:

  * Internal folder structure patterns
  * Source code organization approach
  * Resource organization
  * Project dependencies and references
* **Domain/Feature Organization**:

  * How business domains or features are separated
  * Domain boundary enforcement patterns
* **Layer Organization**:

  * Separation of concerns (Controllers, Services, Repositories, etc.)
  * Layer interaction and dependency patterns
* **Configuration Management**:

  * Configuration file locations and purposes
  * Environment-specific configurations
  * Secret management approach
* **Test Project Organization**:

  * Test project structure and naming
  * Test categories and organization
  * Test data and mock locations" : ""}

${(PROJECT\_TYPE == "React" || PROJECT\_TYPE == "Angular" || PROJECT\_TYPE == "Auto-detect") ? "#### UI Project Structure (if detected)

* **Component Organization**:

  * Component folder structure patterns
  * Grouping strategies (by feature, type, etc.)
  * Shared vs. feature-specific components
* **State Management**:

  * State-related file organization
  * Store structure for global state
  * Local state management patterns
* **Routing Organization**:

  * Route definition locations
  * Page/view component organization
  * Route parameter handling
* **API Integration**:

  * API client organization
  * Service layer structure
  * Data fetching patterns
* **Asset Management**:

  * Static resource organization
  * Image/media file structure
  * Font and icon organization
* **Style Organization**:

  * CSS/SCSS file structure
  * Theme organization
  * Style module patterns" : ""}

### 4\. File Placement Patterns

${INCLUDE\_FILE\_PATTERNS ? "Document the patterns that determine where different types of files should be placed:

* **Configuration Files**:

  * Locations for different types of configuration
  * Environment-specific configuration patterns
* **Model/Entity Definitions**:

  * Where domain models are defined
  * Data transfer object (DTO) locations
  * Schema definition locations
* **Business Logic**:

  * Service implementation locations
  * Business rule organization
  * Utility and helper function placement
* **Interface Definitions**:

  * Where interfaces and abstractions are defined
  * How interfaces are grouped and organized
* **Test Files**:

  * Unit test location patterns
  * Integration test placement
  * Test utility and mock locations
* **Documentation Files**:

  * API documentation placement
  * Internal documentation organization
  * README file distribution" : "Document where key file types are located in the project."}

### 5\. Naming and Organization Conventions

Document the naming and organizational conventions observed across the project:

* **File Naming Patterns**:

  * Case conventions (PascalCase, camelCase, kebab-case)
  * Prefix and suffix patterns
  * Type indicators in filenames
* **Folder Naming Patterns**:

  * Naming conventions for different folder types
  * Hierarchical naming patterns
  * Grouping and categorization conventions
* **Namespace/Module Patterns**:

  * How namespaces/modules map to folder structure
  * Import/using statement organization
  * Internal vs. public API separation
* **Organizational Patterns**:

  * Code co-location strategies
  * Feature encapsulation approaches
  * Cross-cutting concern organization

### 6\. Navigation and Development Workflow

Provide guidance for navigating and working with the codebase structure:

* **Entry Points**:

  * Main application entry points
  * Key configuration starting points
  * Initial files for understanding the project
* **Common Development Tasks**:

  * Where to add new features
  * How to extend existing functionality
  * Where to place new tests
  * Configuration modification locations
* **Dependency Patterns**:

  * How dependencies flow between folders
  * Import/reference patterns
  * Dependency injection registration locations

${INCLUDE\_FILE\_COUNTS ? "- **Content Statistics**:

* Files per directory analysis
* Code distribution metrics
* Complexity concentration areas" : ""}

### 7\. Build and Output Organization

Document the build process and output organization:

* **Build Configuration**:

  * Build script locations and purposes
  * Build pipeline organization
  * Build task definitions
* **Output Structure**:

  * Compiled/built output locations
  * Output organization patterns
  * Distribution package structure
* **Environment-Specific Builds**:

  * Development vs. production differences
  * Environment configuration strategies
  * Build variant organization

### 8\. Technology-Specific Organization

${(PROJECT\_TYPE == ".NET" || PROJECT\_TYPE == "Auto-detect") ? "#### .NET-Specific Structure Patterns (if detected)

* **Project File Organization**:

  * Project file structure and patterns
  * Target framework configuration
  * Property group organization
  * Item group patterns
* **Assembly Organization**:

  * Assembly naming patterns
  * Multi-assembly architecture
  * Assembly reference patterns
* **Resource Organization**:

  * Embedded resource patterns
  * Localization file structure
  * Static web asset organization
* **Package Management**:

  * NuGet configuration locations
  * Package reference organization
  * Package version management" : ""}

${(PROJECT\_TYPE == "Java" || PROJECT\_TYPE == "Auto-detect") ? "#### Java-Specific Structure Patterns (if detected)

* **Package Hierarchy**:

  * Package naming and nesting conventions
  * Domain vs. technical packages
  * Visibility and access patterns
* **Build Tool Organization**:

  * Maven/Gradle structure patterns
  * Module organization
  * Plugin configuration patterns
* **Resource Organization**:

  * Resource folder structures
  * Environment-specific resources
  * Properties file organization" : ""}

${(PROJECT\_TYPE == "Node.js" || PROJECT\_TYPE == "Auto-detect") ? "#### Node.js-Specific Structure Patterns (if detected)

* **Module Organization**:

  * CommonJS vs. ESM organization
  * Internal module patterns
  * Third-party dependency management
* **Script Organization**:

  * npm/yarn script definition patterns
  * Utility script locations
  * Development tool scripts
* **Configuration Management**:

  * Configuration file locations
  * Environment variable management
  * Secret management approaches" : ""}

### 9\. Extension and Evolution

Document how the project structure is designed to be extended:

* **Extension Points**:

  * How to add new modules/features while maintaining conventions
  * Plugin/extension folder patterns
  * Customization directory structures
* **Scalability Patterns**:

  * How the structure scales for larger features
  * Approach for breaking down large modules
  * Code splitting strategies
* **Refactoring Patterns**:

  * Common refactoring approaches observed
  * How structural changes are managed
  * Incremental reorganization patterns

${INCLUDE\_TEMPLATES ? "### 10\. Structure Templates

Provide templates for creating new components that follow project conventions:

* **New Feature Template**:

  * Folder structure for adding a complete feature
  * Required file types and their locations
  * Naming patterns to follow
* **New Component Template**:

  * Directory structure for a typical component
  * Essential files to include
  * Integration points with existing structure
* **New Service Template**:

  * Structure for adding a new service
  * Interface and implementation placement
  * Configuration and registration patterns
* **New Test Structure**:

  * Folder structure for test projects/files
  * Test file organization templates
  * Test resource organization" : ""}

### ${INCLUDE\_TEMPLATES ? "11" : "10"}. Structure Enforcement

Document how the project structure is maintained and enforced:

* **Structure Validation**:

  * Tools/scripts that enforce structure
  * Build checks for structural compliance
  * Linting rules related to structure
* **Documentation Practices**:

  * How structural changes are documented
  * Where architectural decisions are recorded
  * Structure evolution history

Include a section at the end about maintaining this blueprint and when it was last updated. "
