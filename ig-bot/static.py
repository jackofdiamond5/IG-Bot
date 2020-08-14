accept_headers = {
    "machine_man_preview": "application/vnd.github.machine-man-preview+json",
    "inertia_preview": "application/vnd.github.inertia-preview+json",
    "symmetra_preview": "application/vnd.github.symmetra-preview+json",
    "mercy_preview": "application/vnd.github.mercy-preview+json",
}

graphql_endpoint = "https://api.github.com/graphql"
labels_to_skip = ["status: in-review", "status: in-development", "status: resolved"]
target_labels = ["bug", "feature-request"]