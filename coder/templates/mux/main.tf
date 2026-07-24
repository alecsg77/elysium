terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = ">= 2.5"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "coder" {}
provider "kubernetes" {
  config_path = null
}

data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_external_auth" "github" {
  id       = "github"
  optional = true
}

variable "namespace" {
  type        = string
  default     = "coder"
  description = "Kubernetes namespace for workspace pods."
}

data "coder_parameter" "home_disk_size" {
  name         = "home_disk_size"
  display_name = "Home disk size (GiB)"
  description  = "Size of the persistent /home/coder volume. Also stores Docker layer cache and devcontainer state via envbox."
  default      = "20"
  type         = "number"
  icon         = "/emojis/1f4be.png"
  mutable      = false
  validation {
    min = 10
    max = 200
  }
}

data "coder_parameter" "cpu_limit" {
  name         = "cpu_limit"
  display_name = "CPU limit (cores)"
  default      = "2"
  type         = "number"
  icon         = "/icon/memory.svg"
  mutable      = true
  validation {
    min = 1
    max = 16
  }
}

data "coder_parameter" "memory_limit" {
  name         = "memory_limit"
  display_name = "Memory limit (GiB)"
  default      = "4"
  type         = "number"
  icon         = "/icon/memory.svg"
  mutable      = true
  validation {
    min = 2
    max = 32
  }
}

resource "coder_agent" "main" {
  os                         = "linux"
  arch                       = "amd64"
  connection_timeout = 300

  # GITHUB_COPILOT_TOKEN: lets mux use GitHub Copilot natively (provider: github-copilot),
  # avoiding copilot-api which sends Azure OpenAI preamble chunks that break streaming.
  # GITHUB_PERSONAL_ACCESS_TOKEN: same token, required by the GitHub MCP server
  # (@modelcontextprotocol/server-github) for API access to repos, issues, and PRs.
  env = {
    GITHUB_COPILOT_TOKEN         = data.coder_external_auth.github.access_token
    GITHUB_PERSONAL_ACCESS_TOKEN = data.coder_external_auth.github.access_token
  }

  metadata {
    display_name = "CPU Usage"
    key          = "0_cpu_usage"
    script       = "coder stat cpu"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "RAM Usage"
    key          = "1_ram_usage"
    script       = "coder stat mem"
    interval     = 10
    timeout      = 1
  }

  metadata {
    display_name = "Docker"
    key          = "2_docker"
    script       = "docker info --format '{{.ServerVersion}}' 2>/dev/null && echo 'running' || echo 'unavailable'"
    interval     = 30
    timeout      = 5
  }
}

# Sets CODER_SESSION_TOKEN = data.coder_workspace_owner.me.session_token and
# CODER_URL = data.coder_workspace.me.access_url as workspace env vars.
# The mux process (started by the mux module script) inherits these, providing
# automatic Coder authentication without any manually managed token or secret.
module "coder-login" {
  count    = data.coder_workspace.me.start_count
  source   = "registry.coder.com/coder/coder-login/coder"
  version  = "1.1.1"
  agent_id = coder_agent.main.id
}

# Installs mux@next via npm (falls back to tarball) and runs the mux server as
# a workspace process. Generates its own MUX_SERVER_AUTH_TOKEN per workspace
# instance (stored in Terraform state -- no manual secret management needed).
module "mux" {
  count           = data.coder_workspace.me.start_count
  source          = "registry.coder.com/coder/mux/coder"
  version         = "1.4.3"
  agent_id        = coder_agent.main.id
  subdomain       = false
  restart_on_kill = true
  # Store binary and log on the persistent PVC (home dir) so they survive workspace restarts.
  # use_cached skips reinstall when the binary is already present.
  install_prefix = "/home/coder/.local/bin"
  log_path       = "/home/coder/.mux/mux.log"
  use_cached     = true
}

# Installs @devcontainers/cli via npm. npm is pre-installed in the inner image.
# start_blocks_login=false so a transient failure does not mark workspace unhealthy.
module "devcontainers-cli" {
  count              = data.coder_workspace.me.start_count
  source             = "registry.coder.com/coder/devcontainers-cli/coder"
  version            = "1.1.0"
  agent_id           = coder_agent.main.id
  start_blocks_login = false
}

module "git-config" {
  count              = data.coder_workspace.me.start_count
  source             = "registry.coder.com/coder/git-config/coder"
  version            = "1.0.34"
  agent_id           = coder_agent.main.id
  allow_email_change = true
}

module "github-upload-public-key" {
  count            = data.coder_external_auth.github.access_token != "" ? data.coder_workspace.me.start_count : 0
  source           = "registry.coder.com/coder/github-upload-public-key/coder"
  version          = "1.0.32"
  agent_id         = coder_agent.main.id
  external_auth_id = data.coder_external_auth.github.id
}

resource "kubernetes_persistent_volume_claim" "home" {
  metadata {
    name      = "coder-${data.coder_workspace.me.id}-home"
    namespace = var.namespace
    labels = {
      "app.kubernetes.io/name"     = "coder-pvc"
      "app.kubernetes.io/instance" = "coder-pvc-${data.coder_workspace.me.id}"
      "app.kubernetes.io/part-of"  = "coder"
      "com.coder.resource"         = "true"
      "com.coder.workspace.id"     = data.coder_workspace.me.id
      "com.coder.workspace.name"   = data.coder_workspace.me.name
      "com.coder.user.id"          = data.coder_workspace_owner.me.id
      "com.coder.user.username"    = data.coder_workspace_owner.me.name
    }
    annotations = {
      "com.coder.user.email" = data.coder_workspace_owner.me.email
    }
  }
  wait_until_bound = false
  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "${data.coder_parameter.home_disk_size.value}Gi"
      }
    }
  }
  lifecycle {
    ignore_changes = all
  }
}

resource "kubernetes_pod" "main" {
  count = data.coder_workspace.me.start_count
  metadata {
    name      = "coder-${data.coder_workspace.me.id}"
    namespace = var.namespace
    labels = {
      "app.kubernetes.io/name"     = "coder-workspace"
      "app.kubernetes.io/instance" = "coder-workspace-${data.coder_workspace.me.id}"
      "app.kubernetes.io/part-of"  = "coder"
      "com.coder.resource"         = "true"
      "com.coder.workspace.id"     = data.coder_workspace.me.id
      "com.coder.workspace.name"   = data.coder_workspace.me.name
      "com.coder.user.id"          = data.coder_workspace_owner.me.id
      "com.coder.user.username"    = data.coder_workspace_owner.me.name
    }
    annotations = {
      "com.coder.user.email" = data.coder_workspace_owner.me.email
    }
  }
  spec {
    restart_policy = "Never"

    container {
      name              = "dev"
      image             = "ghcr.io/coder/envbox:0.6.7"
      image_pull_policy = "IfNotPresent"
      command           = ["/envbox", "docker"]

      security_context {
        privileged = true
      }

      resources {
        requests = {
          cpu    = "250m"
          memory = "512Mi"
        }
        limits = {
          cpu    = "${data.coder_parameter.cpu_limit.value}"
          memory = "${data.coder_parameter.memory_limit.value}Gi"
        }
      }

      env {
        name  = "CODER_AGENT_TOKEN"
        value = coder_agent.main.token
      }
      env {
        name  = "CODER_AGENT_URL"
        value = data.coder_workspace.me.access_url
      }
      env {
        name  = "CODER_INNER_IMAGE"
        value = "codercom/enterprise-node:ubuntu-20260723"
      }
      env {
        name  = "CODER_INNER_USERNAME"
        value = "coder"
      }
      env {
        name  = "CODER_BOOTSTRAP_SCRIPT"
        value = coder_agent.main.init_script
      }
      env {
        name  = "CODER_MOUNTS"
        value = "/home/coder:/home/coder"
      }
      env {
        name  = "CODER_ADD_FUSE"
        value = "false"
      }
      env {
        name  = "CODER_ADD_TUN"
        value = "false"
      }
      env {
        name  = "CODER_INNER_HOSTNAME"
        value = data.coder_workspace.me.name
      }
      env {
        name = "CODER_CPUS"
        value_from {
          resource_field_ref {
            resource = "limits.cpu"
          }
        }
      }
      env {
        name = "CODER_MEMORY"
        value_from {
          resource_field_ref {
            resource = "limits.memory"
          }
        }
      }

      volume_mount {
        mount_path = "/home/coder"
        name       = "home"
        sub_path   = "home"
      }
      volume_mount {
        mount_path = "/var/lib/coder/docker"
        name       = "home"
        sub_path   = "cache/docker"
      }
      volume_mount {
        mount_path = "/var/lib/coder/containers"
        name       = "home"
        sub_path   = "cache/containers"
      }
      volume_mount {
        mount_path = "/var/lib/sysbox"
        name       = "sysbox"
      }
      volume_mount {
        mount_path = "/var/lib/containers"
        name       = "home"
        sub_path   = "envbox/containers"
      }
      volume_mount {
        mount_path = "/var/lib/docker"
        name       = "home"
        sub_path   = "envbox/docker"
      }
      volume_mount {
        mount_path = "/usr/src"
        name       = "usr-src"
      }
      volume_mount {
        mount_path = "/lib/modules"
        name       = "lib-modules"
      }
    }

    volume {
      name = "home"
      persistent_volume_claim {
        claim_name = kubernetes_persistent_volume_claim.home.metadata[0].name
      }
    }
    volume {
      name = "sysbox"
      empty_dir {}
    }
    volume {
      name = "usr-src"
      host_path {
        path = "/usr/src"
        type = ""
      }
    }
    volume {
      name = "lib-modules"
      host_path {
        path = "/lib/modules"
        type = ""
      }
    }
  }
}

resource "coder_metadata" "workspace_info" {
  count       = data.coder_workspace.me.start_count
  resource_id = kubernetes_pod.main[0].id
  item {
    key   = "image"
    value = "ghcr.io/coder/envbox:0.6.7"
  }
  item {
    key   = "inner_image"
    value = "codercom/enterprise-node:ubuntu-20260713"
  }
  item {
    key   = "cpu"
    value = "${data.coder_parameter.cpu_limit.value} cores"
  }
  item {
    key   = "memory"
    value = "${data.coder_parameter.memory_limit.value} GiB"
  }
  item {
    key   = "home_disk"
    value = "${data.coder_parameter.home_disk_size.value} GiB"
  }
}
