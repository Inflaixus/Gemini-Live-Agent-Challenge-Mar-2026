output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.agent.uri
}

output "image_url" {
  description = "Container image URL"
  value       = local.image_url
}
