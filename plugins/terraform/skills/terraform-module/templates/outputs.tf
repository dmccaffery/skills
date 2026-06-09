# Outputs. Every output carries a description (tflint enforces this).
# Outputs read as module.<name>.<output> — never repeat the module concept in
# the output name (module.cluster.endpoint, not module.cluster.cluster_endpoint).

# The primary resource's own top-level attributes stay flat.
output "name" {
  description = "Name of the primary resource."
  value       = PROVIDER_TYPE.main.name
}

output "arn" {
  description = "ARN of the primary resource."
  value       = PROVIDER_TYPE.main.arn
}

# Cohesive facets of one concept are grouped into a single object output named
# for the concept — a shared prefix across flat outputs is the signal to fold.
output "node_role" {
  description = "IAM role shared by worker nodes."
  value = {
    arn  = null # e.g. aws_iam_role.node.arn
    name = null # e.g. aws_iam_role.node.name
  }
}
