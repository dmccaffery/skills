# Primary resources. Naming: the module's single primary resource is "main";
# a for_each fan-out resource is a singular noun (e.g. "repo"); a secondary
# singleton is a purpose word (e.g. "retention", "irsa"). Never "this".

resource "PROVIDER_TYPE" "main" {
  # For resources whose name is unique per account/region (IAM roles, security
  # groups, launch templates), prefer name_prefix with a trailing "-":
  #   name_prefix = "${var.name}-"        # ≤ 38 chars before the random suffix

  # Gate an optional resource with for_each over a one-or-zero-element set,
  # not count:
  #   for_each = toset(var.enabled ? ["true"] : [])
}
