# Inputs. Every variable carries a description (tflint enforces this).
# Use set(string) for unordered unique collections. Optional strings default
# to null (optional(string) with no second argument), never "".

variable "name" {
  description = "Name the module's resources derive theirs from."
  type        = string
}

variable "subnet_ids" {
  description = "Subnets the resources span (unordered, unique)."
  type        = set(string)
}

# Group variables that are always configured together into one object with
# optional() attributes and default = {}, so `module "x" {}` still applies
# and callers set only what they need. Group only genuinely cohesive knobs.
variable "endpoint_access" {
  description = "How the endpoint is exposed."
  type = object({
    private      = optional(bool, true)
    public       = optional(bool, false)
    public_cidrs = optional(set(string), [])
  })
  default = {}
}
