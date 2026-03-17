# Build and push Docker image via Cloud Build
resource "null_resource" "docker_build" {
  triggers = {
    # Rebuild when source, config, KB, or UI changes
    app_hash = sha256(join("", [
      filesha256("${path.module}/../app/main.py"),
      filesha256("${path.module}/../app/agents/patient_agent.py"),
      filesha256("${path.module}/../Dockerfile"),
      filesha256("${path.module}/../pyproject.toml"),
      filesha256("${path.module}/../../ui/package.json"),
      filesha256("${path.module}/../../ui/App.tsx"),
    ]))
  }

  provisioner "local-exec" {
    # Use project root as build context so both Live-Agent-New-Version/ and ui/ are accessible
    working_dir = "${path.module}/../.."
    command     = <<-EOT
      BUILD_ID=$(gcloud builds submit . \
        --config cloudbuild.yaml \
        --substitutions _IMAGE_URL=${local.image_url} \
        --project ${var.project_id} \
        --async \
        --format='value(id)') \
      && echo "Build submitted: $BUILD_ID" \
      && while true; do \
           STATUS=$(gcloud builds describe "$BUILD_ID" \
             --project ${var.project_id} \
             --format='value(status)'); \
           echo "Build status: $STATUS"; \
           case "$STATUS" in \
             SUCCESS) break ;; \
             FAILURE|CANCELLED|TIMEOUT|INTERNAL_ERROR) \
               echo "Build failed with status: $STATUS" && exit 1 ;; \
           esac; \
           sleep 30; \
         done
    EOT
  }

  depends_on = [google_artifact_registry_repository.repo]
}

# Cloud Run service
resource "google_cloud_run_v2_service" "agent" {
  name     = var.service_name
  location = var.region

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = local.image_url

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }

      # App configuration
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "FALSE"
      }
      env {
        name  = "GOOGLE_API_KEY"
        value = var.google_api_key
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "AGENT_MODEL"
        value = var.agent_model
      }
      env {
        name  = "VOICE_NAME"
        value = var.voice_name
      }
      env {
        name  = "LIVE_RESPONSE_MODALITY"
        value = "AUDIO"
      }
      env {
        name  = "SCENARIO"
        value = var.scenario
      }
      env {
        name  = "OUTPUT_AUDIO_TRANSCRIPTION_ENABLED"
        value = "true"
      }
      env {
        name  = "SILENCE_DURATION_MS"
        value = "140"
      }
      env {
        name  = "PREFIX_PADDING_MS"
        value = "10"
      }
      env {
        name  = "TURN_COVERAGE_MODE"
        value = "all_input"
      }
      env {
        name  = "ENABLE_AFFECTIVE_DIALOG"
        value = "true"
      }
      env {
        name  = "ENABLE_PROACTIVITY"
        value = "true"
      }

      # WebSocket session affinity timeout
      startup_probe {
        http_get {
          path = "/"
        }
        initial_delay_seconds = 5
        period_seconds        = 10
      }
    }

    # Required for WebSocket support
    session_affinity = true

    # Long timeout for live streaming sessions
    timeout = "3600s"
  }

  depends_on = [
    google_project_service.apis,
    null_resource.docker_build,
  ]
}

# Allow unauthenticated access (public)
resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agent.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
