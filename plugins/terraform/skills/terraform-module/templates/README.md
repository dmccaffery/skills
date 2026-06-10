# MODULE_NAME

One paragraph: what this module manages and the design decisions a caller must know (what it deliberately does not do,
what it assumes already exists).

## Usage

```hcl
module "MODULE_NAME" {
  source = "../../modules/MODULE_NAME"

  name       = "example"
  subnet_ids = ["subnet-aaa", "subnet-bbb"]

  endpoint_access = {
    public = true
  }
}
```

## Inputs

| Name              | Description                                     | Type          | Default |
| ----------------- | ----------------------------------------------- | ------------- | ------- |
| `name`            | Name the module's resources derive theirs from. | `string`      | —       |
| `subnet_ids`      | Subnets the resources span.                     | `set(string)` | —       |
| `endpoint_access` | How the endpoint is exposed.                    | `object`      | `{}`    |

## Outputs

| Name        | Description                   |
| ----------- | ----------------------------- |
| `name`      | Name of the primary resource. |
| `arn`       | ARN of the primary resource.  |
| `node_role` | Object: `arn`, `name`.        |

See `variables.tf` and `outputs.tf` for the exhaustive reference.
