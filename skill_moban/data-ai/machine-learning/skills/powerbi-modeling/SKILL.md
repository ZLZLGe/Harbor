# Power BI Semantic Modeling

Guide users in building optimized, well-documented Power BI semantic models following Microsoft best practices.

## When to Use This Skill

Use this skill when users ask about:

* Creating or optimizing Power BI semantic models
* Designing star schemas (dimension/fact tables)
* Writing DAX measures or calculated columns
* Configuring table relationships (cardinality, cross-filter)
* Implementing row-level security (RLS)
* Naming conventions for tables, columns, measures
* Adding descriptions and documentation to models
* Performance tuning and optimization
* Calculation groups and field parameters
* Model validation and best practice checks

**Trigger phrases:** "create a measure", "add relationship", "star schema", "optimize model", "DAX formula", "RLS", "naming convention", "model documentation", "cardinality", "cross-filter"

## Prerequisites

### Required Tools

* **Power BI Modeling MCP Server**: Required for connecting to and modifying semantic models  
  * Enables: connection\_operations, table\_operations, measure\_operations, relationship\_operations, etc.
  * Must be configured and running to interact with models

### Optional Dependencies

* **Microsoft Learn MCP Server**: Recommended for researching latest best practices  
  * Enables: microsoft\_docs\_search, microsoft\_docs\_fetch
  * Use for complex scenarios, new features, and official documentation

## Workflow

### 1\. Connect and Analyze First

Before providing any modeling guidance, always examine the current model state:

```text
1. List connections: connection_operations(operation: "ListConnections")
2. If no connection, check for local instances: connection_operations(operation: "ListLocalInstances")
3. Connect to the model (Desktop or Fabric)
4. Get model overview: model_operations(operation: "Get")
5. List tables: table_operations(operation: "List")
6. List relationships: relationship_operations(operation: "List")
7. List measures: measure_operations(operation: "List")

```

### 2\. Evaluate Model Health

After connecting, assess the model against best practices:

* **Star Schema**: Are tables properly classified as dimension or fact?
* **Relationships**: Correct cardinality? Minimal bidirectional filters?
* **Naming**: Human-readable, consistent naming conventions?
* **Documentation**: Do tables, columns, measures have descriptions?
* **Measures**: Explicit measures for key calculations?
* **Hidden Fields**: Are technical columns hidden from report view?

### 3\. Provide Targeted Guidance

Based on analysis, guide improvements using references:

* Star schema design: See [STAR-SCHEMA.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/powerbi-modeling/references/STAR-SCHEMA.md)
* Relationship configuration: See [RELATIONSHIPS.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/powerbi-modeling/references/RELATIONSHIPS.md)
* DAX measures and naming: See [MEASURES-DAX.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/powerbi-modeling/references/MEASURES-DAX.md)
* Performance optimization: See [PERFORMANCE.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/powerbi-modeling/references/PERFORMANCE.md)
* Row-level security: See [RLS.md](https://github.com/github/awesome-copilot/blob/HEAD/skills/powerbi-modeling/references/RLS.md)

## Quick Reference: Model Quality Checklist

| Area          | Best Practice                               |
| ------------- | ------------------------------------------- |
| Tables        | Clear dimension vs fact classification      |
| Naming        | Human-readable: Customer Name not CUST\_NM  |
| Descriptions  | All tables, columns, measures documented    |
| Measures      | Explicit DAX measures for business metrics  |
| Relationships | One-to-many from dimension to fact          |
| Cross-filter  | Single direction unless specifically needed |
| Hidden fields | Hide technical keys, IDs from report view   |
| Date table    | Dedicated marked date table                 |

## MCP Tools Reference

Use these Power BI Modeling MCP operations:

| Operation Category             | Key Operations                                              |
| ------------------------------ | ----------------------------------------------------------- |
| connection\_operations         | Connect, ListConnections, ListLocalInstances, ConnectFabric |
| model\_operations              | Get, GetStats, ExportTMDL                                   |
| table\_operations              | List, Get, Create, Update, GetSchema                        |
| column\_operations             | List, Get, Create, Update (descriptions, hidden, format)    |
| measure\_operations            | List, Get, Create, Update, Move                             |
| relationship\_operations       | List, Get, Create, Update, Activate, Deactivate             |
| dax\_query\_operations         | Execute, Validate                                           |
| calculation\_group\_operations | List, Create, Update                                        |
| security\_role\_operations     | List, Create, Update, GetEffectivePermissions               |

## Common Tasks

### Add Measure with Description

```text
measure_operations(
  operation: "Create",
  definitions: [{
    name: "Total Sales",
    tableName: "Sales",
    expression: "SUM(Sales[Amount])",
    formatString: "$#,##0",
    description: "Sum of all sales amounts"
  }]
)

```

### Update Column Description

```text
column_operations(
  operation: "Update",
  definitions: [{
    tableName: "Customer",
    name: "CustomerKey",
    description: "Unique identifier for customer dimension",
    isHidden: true
  }]
)

```

### Create Relationship

```text
relationship_operations(
  operation: "Create",
  definitions: [{
    fromTable: "Sales",
    fromColumn: "CustomerKey",
    toTable: "Customer",
    toColumn: "CustomerKey",
    crossFilteringBehavior: "OneDirection"
  }]
)

```

## When to Use Microsoft Learn MCP

Research current best practices using `microsoft_docs_search` for:

* Latest DAX function documentation
* New Power BI features and capabilities
* Complex modeling scenarios (SCD Type 2, many-to-many)
* Performance optimization techniques
* Security implementation patterns
