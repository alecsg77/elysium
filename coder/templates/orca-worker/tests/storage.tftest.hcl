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
run "running" {
  command = apply
  assert {
    condition     = length(kubernetes_persistent_volume_claim_v1.data) == 2
    error_message = "Home and project storage must be separate persistent resources."
  }
  assert {
    condition = alltrue([
      for mount in kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].volume_mount :
      contains(["/home/coder", "/workspaces"], mount.mount_path)
    ]) && length(kubernetes_deployment_v1.main[0].spec[0].template[0].spec[0].container[0].volume_mount) == 2
    error_message = "The agent container must mount both the complete home and projects."
  }
}
run "stopped" {
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
    condition     = length(kubernetes_deployment_v1.main) == 0
    error_message = "A Coder stop must remove project compute."
  }
  assert {
    condition     = output.home_claim_id == run.running.home_claim_id && output.projects_claim_id == run.running.projects_claim_id
    error_message = "Stopping the workspace must retain both existing PVC identities."
  }
}

run "resumed" {
  command = plan
  assert {
    condition     = length(kubernetes_deployment_v1.main) == 1 && output.home_claim_id == run.running.home_claim_id && output.projects_claim_id == run.running.projects_claim_id
    error_message = "Resuming compute must reuse the original home and project PVCs."
  }
}
