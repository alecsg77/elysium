terraform {
  required_version = ">= 1.9"
  required_providers {
    coder = {
      source  = "coder/coder"
      version = ">= 2.12, < 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 3.2"
    }
  }
}
provider "coder" {}
provider "kubernetes" {}
variable "namespace" {
  type        = string
  default     = "coder"
  description = "Existing namespace used by the Coder provisioner."
}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}
data "coder_external_auth" "github" {
  id       = "github"
  optional = true
}
data "coder_parameter" "repo" {
  name         = "repo"
  display_name = "Project repository"
  description  = "HTTPS Git URL without embedded credentials; GitHub external auth is used when available."
  type         = "string"
  mutable      = false
  validation {
    regex = "^https://[^@[:space:]]+$"
    error = "Use an HTTPS repository URL without embedded credentials."
  }
}
data "coder_parameter" "devcontainer_dir" {
  name         = "devcontainer_dir"
  display_name = "Devcontainer directory"
  description  = "Directory relative to the project checkout."
  type         = "string"
  default      = ".devcontainer"
  mutable      = true
}
data "coder_parameter" "cpu" {
  name    = "cpu"
  type    = "number"
  default = "2"
  mutable = true
  validation {
    min = 1
    max = 16
  }
}
data "coder_parameter" "memory" {
  name         = "memory"
  display_name = "Memory (GiB)"
  type         = "number"
  default      = "4"
  mutable      = true
  validation {
    min = 2
    max = 32
  }
}
data "coder_parameter" "disk" {
  name         = "disk"
  display_name = "Size of each data volume (GiB)"
  description  = "Separate persistent volumes for the complete home and project files."
  type         = "number"
  default      = "20"
  mutable      = false
  validation {
    min = 10
    max = 200
  }
}
locals {
  name = "coder-${data.coder_workspace.me.id}-orca"
  labels = {
    "app.kubernetes.io/name"   = "coder-orca-worker"
    "com.coder.workspace.id"   = data.coder_workspace.me.id
    "com.coder.workspace.name" = data.coder_workspace.me.name
    "com.coder.user.id"        = data.coder_workspace_owner.me.id
    "com.coder.resource"       = "true"
  }
}
# Storage must outlive the deployment removed by a normal Coder stop.
resource "kubernetes_persistent_volume_claim_v1" "data" {
  for_each = toset(["home", "workspaces"])
  metadata {
    name      = "${local.name}-${each.key}"
    namespace = var.namespace
    labels    = local.labels
  }
  wait_until_bound = false
  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = { storage = "${data.coder_parameter.disk.value}Gi" }
    }
  }
  lifecycle {
    ignore_changes = [metadata, spec]
  }
}
resource "coder_agent" "main" {
  os   = "linux"
  arch = "amd64"
  dir  = "/workspaces/project"
  env = {
    HOME       = "/home/coder"
    CODEX_HOME = "/home/coder/.codex"
  }
  startup_script = <<-EOT
    set -eu
    mkdir -p "$HOME/.config" "$HOME/.local/share" "$HOME/.local/state" "$HOME/.codex"
  EOT
  metadata {
    key          = "memory"
    display_name = "Memory"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }
}
resource "kubernetes_deployment_v1" "main" {
  count = data.coder_workspace.me.start_count
  metadata {
    name      = local.name
    namespace = var.namespace
    labels    = local.labels
  }
  spec {
    replicas = 1
    selector {
      match_labels = { "com.coder.workspace.id" = data.coder_workspace.me.id }
    }
    strategy {
      type = "Recreate"
    }
    template {
      metadata {
        labels = local.labels
      }
      spec {
        automount_service_account_token = false
        node_selector                   = { "kubernetes.io/arch" = "amd64" }
        init_container {
          name    = "home-owner"
          image   = "busybox:1.38.0"
          command = ["sh", "-ec", "chown 1000:1000 /home/coder /workspaces; chmod 0700 /home/coder"]
          volume_mount {
            name       = "home"
            mount_path = "/home/coder"
          }
          volume_mount {
            name       = "workspaces"
            mount_path = "/workspaces"
          }
        }
        container {
          name  = "dev"
          image = "ghcr.io/coder/envbuilder:1.3.0"
          security_context {
            privileged = true
          }
          resources {
            requests = { cpu = "250m", memory = "512Mi" }
            limits   = { cpu = data.coder_parameter.cpu.value, memory = "${data.coder_parameter.memory.value}Gi" }
          }
          dynamic "env" {
            for_each = {
              CODER_AGENT_URL                  = data.coder_workspace.me.access_url
              CODER_AGENT_TOKEN                = coder_agent.main.token
              ENVBUILDER_GIT_URL               = data.coder_parameter.repo.value
              ENVBUILDER_WORKSPACE_FOLDER      = "/workspaces/project"
              ENVBUILDER_DEVCONTAINER_DIR      = data.coder_parameter.devcontainer_dir.value
              ENVBUILDER_IGNORE_PATHS          = "/var/run,/product_uuid,/product_name,/home/coder"
              ENVBUILDER_EXIT_ON_BUILD_FAILURE = "true"
              ENVBUILDER_GIT_USERNAME          = data.coder_external_auth.github.access_token != "" ? "x-access-token" : ""
              ENVBUILDER_GIT_PASSWORD          = data.coder_external_auth.github.access_token
              ENVBUILDER_SETUP_SCRIPT          = file("${path.module}/scripts/check-user.sh")
              ENVBUILDER_INIT_SCRIPT           = "export PATH=\"$HOME/.local/bin:$PATH\"\n${coder_agent.main.init_script}"
            }
            iterator = setting
            content {
              name  = setting.key
              value = setting.value
            }
          }
          volume_mount {
            name       = "home"
            mount_path = "/home/coder"
          }
          volume_mount {
            name       = "workspaces"
            mount_path = "/workspaces"
          }
        }
        dynamic "volume" {
          for_each = kubernetes_persistent_volume_claim_v1.data
          content {
            name = volume.key
            persistent_volume_claim {
              claim_name = volume.value.metadata[0].name
            }
          }
        }
      }
    }
  }
}
module "codex" {
  count         = data.coder_workspace.me.start_count
  source        = "registry.coder.com/coder-labs/codex/coder"
  version       = "5.5.0"
  agent_id      = coder_agent.main.id
  workdir       = "/workspaces/project"
  codex_version = "0.166.0"
  manage_config = false
}
resource "coder_script" "opencode" {
  count              = data.coder_workspace.me.start_count
  agent_id           = coder_agent.main.id
  display_name       = "Install OpenCode"
  run_on_start       = true
  start_blocks_login = true
  script             = file("${path.module}/scripts/install-opencode.sh")
}
module "git_config" {
  count              = data.coder_workspace.me.start_count
  source             = "registry.coder.com/coder/git-config/coder"
  version            = "1.0.35"
  agent_id           = coder_agent.main.id
  allow_email_change = true
}
output "home_claim_id" {
  value = kubernetes_persistent_volume_claim_v1.data["home"].id
}
output "projects_claim_id" {
  value = kubernetes_persistent_volume_claim_v1.data["workspaces"].id
}
