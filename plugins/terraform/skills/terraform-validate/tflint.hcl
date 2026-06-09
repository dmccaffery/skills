# Reference tflint configuration — seed a repository's .tflint.hcl from this file.

config {
  # Lint module blocks called from this configuration (local modules only).
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# Provider-specific rulesets are opt-in: uncomment (and pin) only the one the
# repository actually targets. Downloaded by `tflint --init` (needs network).
#
# plugin "aws" {
#   enabled = true
#   version = "0.39.0"
#   source  = "github.com/terraform-linters/tflint-ruleset-aws"
# }

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}
