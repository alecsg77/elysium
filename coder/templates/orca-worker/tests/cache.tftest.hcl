mock_provider "coder" {
  mock_data "coder_workspace" {
    defaults = {
      id          = "11111111-1111-4111-8111-111111111111"
      name        = "orca-test"
      start_count = 1
      access_url  = "https://coder.example.com"
    }
  }
  mock_data "coder_workspace_owner" {
    defaults = {
      id    = "22222222-2222-4222-8222-222222222222"
      name  = "test-user"
      email = "test@example.com"
    }
  }
  mock_data "coder_external_auth" {
    defaults = { access_token = "" }
  }
}
mock_provider "kubernetes" {}
mock_provider "envbuilder" {}
override_data {
  target = data.coder_parameter.repo
  values = { value = "https://example.com/project.git" }
}
override_data {
  target = data.coder_parameter.devcontainer_dir
  values = { value = ".devcontainer" }
}
override_data {
  target = data.coder_parameter.cpu
  values = { value = "2" }
}
override_data {
  target = data.coder_parameter.memory
  values = { value = "4" }
}
override_data {
  target = data.coder_parameter.disk
  values = { value = "20" }
}
variables {
  cache_repo          = "registry.example.com/devcontainer"
  insecure_cache_repo = false
  use_cached_image    = true
}
run "cache_miss" {
  command = apply
  override_resource {
    target = envbuilder_cached_image.main[0]
    values = { image = "ghcr.io/coder/envbuilder:1.3.0", exists = false }
  }
  assert {
    condition     = kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].image == "ghcr.io/coder/envbuilder:1.3.0"
    error_message = "A cache miss must start Envbuilder rather than prevent workspace creation."
  }
}
run "stop_between_probes" {
  command = apply
  override_data {
    target = data.coder_workspace.me
    values = {
      id          = "11111111-1111-4111-8111-111111111111"
      name        = "orca-test"
      start_count = 0
      access_url  = "https://coder.example.com"
    }
  }
  assert {
    condition     = length(envbuilder_cached_image.main) == 0 && output.home_claim_id == run.cache_miss.home_claim_id && output.projects_claim_id == run.cache_miss.projects_claim_id
    error_message = "Stopping must remove the probe so the next start checks remote build inputs, while retaining storage."
  }
}
run "cache_hit" {
  command = apply
  override_resource {
    target = envbuilder_cached_image.main[0]
    values = { image = "registry.example.com/devcontainer@sha256:fixture", exists = true }
  }
  assert {
    condition     = kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].image == "registry.example.com/devcontainer@sha256:fixture"
    error_message = "A full-image cache hit must select the immutable digest."
  }
  assert {
    condition     = output.home_claim_id == run.cache_miss.home_claim_id && output.projects_claim_id == run.cache_miss.projects_claim_id
    error_message = "Switching to a cached image must preserve both existing PVC identities."
  }
  assert {
    condition = {
      for env in kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].env : env.name => env.value
    }["ENVBUILDER_WORKSPACE_FOLDER"] == "/workspaces/project"
    error_message = "The provider's temporary clone path must never replace the persistent checkout path."
  }
}
run "layers_without_native_registry_pull" {
  command = plan
  variables { use_cached_image = false }
  assert {
    condition     = length(envbuilder_cached_image.main) == 0 && kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].image == "ghcr.io/coder/envbuilder:1.3.0"
    error_message = "Layer caching must not require the node runtime to pull the internal registry."
  }
  assert {
    condition = {
      for env in kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].env : env.name => env.value
    }["ENVBUILDER_CACHE_REPO"] == var.cache_repo
    error_message = "Disabling full-image pulls must retain shared layer caching inside Envbuilder."
  }
}
run "cache_disabled" {
  command = plan
  variables {
    cache_repo       = ""
    use_cached_image = false
  }
  assert {
    condition = length(envbuilder_cached_image.main) == 0 && {
      for env in kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].env : env.name => env.value
    }["ENVBUILDER_REMOTE_REPO_BUILD_MODE"] == "false"
    error_message = "Disabling caching must restore builds from the persistent local checkout."
  }
}
