provider "coder" {}
mock_provider "kubernetes" {}
mock_provider "envbuilder" {}

override_data {
  target = data.coder_workspace.me
  values = {
    id          = "11111111-1111-4111-8111-111111111111"
    name        = "orca-import-test"
    start_count = 1
    access_url  = "https://coder.example.com"
  }
}
override_data {
  target = data.coder_workspace_owner.me
  values = {
    id    = "22222222-2222-4222-8222-222222222222"
    name  = "test-user"
    email = "test@example.com"
  }
}
override_data {
  target = data.coder_external_auth.github
  values = { access_token = "" }
}
override_module {
  target = module.codex
}
override_module {
  target = module.git_config
}

run "import_without_workspace_parameters" {
  command = plan
  variables {
    cache_repo       = "registry.example.com/devcontainer"
    use_cached_image = true
  }
  assert {
    condition     = length(envbuilder_cached_image.main) == 0
    error_message = "Template import must not clone or probe an unset repository."
  }
  assert {
    condition     = !data.coder_parameter.repo.optional && data.coder_parameter.repo.value == ""
    error_message = "Template import must accept an unset repository while keeping it required for workspace creation."
  }
  assert {
    condition = can(regex(data.coder_parameter.repo.validation[0].regex, "https://example.com/project.git")) && !can(regex(
      data.coder_parameter.repo.validation[0].regex, "https://example.com/project name.git"
    ))
    error_message = "Backend validation must accept HTTPS repository URLs and reject whitespace."
  }
}
