# Pipeline Templates

> NOTE: This feature is under development, and not currently functional. These documents will be updated alongside the code.

Occasionally there will be a need for the deployment / update of one resource to affect a change in another. This section outlines how that can be achieved with Pipeline Templates.

## Overview
A pipeline template is an optional `pipeline: {}` block that can be added to the top level of a resource schema document. It allows a template developer to define actions to run against other resources before and after the primary resource is deployed.

### Example
Consider the following `template_schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema",
  "$id": "https://github.com/microsoft/AzureTRE/templates/workspace_services/guacamole/user_resources/guacamole-dev-vm/template_schema.json",
  ...
  "properties": {...},
  "pipeline": {
    "install": [
      {
        "step_id": "6d2d7eb7-984e-4330-bd3c-c7ec98658402",
        "resource_template_name": "tre-shared-service-firewall",
        "resource_type": "shared_service",
        "resource_action": "upgrade",
        "properties": [
        {
          "name": "display_name",
          "type": "string",
          "value": "A new name here!"
        }]
      },
      {
        "step_id": "main"
      },
      {
        "step_id": "2fe8a6a7-2c27-4c49-8773-127df8a48b4e",
        ...
      }
    ]
  }
}
```

When a user deploys this resource, the API will read the `install: []` array within the `pipeline: {}` block, and will:
- Orchestrate the `upgrade` of the `tre-shared-service-firewall`.
- Run the `main` (primary resource) install
- Complete the next step

A single `Operation` document will be used to keep track of which steps in the deployment chain have completed.

## Current Limitations
This feature is very much a work in progress, and is currently limited in the following ways:
- Only statically addressable resources can be referred to - such as `shared_services`, as these are singletons and can be referenced by a template name.
- Only the `upgrade` action for each secondary resource is supported. Support for `install` / `uninstall` is planned.
- Properties only accept static values. Runtime value substitution is planned.
- Only `install` is supported for the 'trigger' for the primary resource. `upgrade` and `uninstall` support is planned.
- No current planned support for `customActions`.
