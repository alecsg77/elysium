provider "coder" {}
mock_provider "kubernetes" {}

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
  assert {
    condition     = !data.coder_parameter.repo.optional && data.coder_parameter.repo.value == ""
    error_message = "Template import must accept an unset repository while keeping it required for workspace creation."
  }
}
