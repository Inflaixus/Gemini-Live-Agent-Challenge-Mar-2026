variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "x-sorter-489913-c0"
}

variable "region" {
  description = "GCP region for Cloud Run"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "bilingual-audio-agent"
}

variable "google_api_key" {
  description = "Google AI Studio API key"
  type        = string
  sensitive   = true
}

variable "agent_model" {
  description = "Gemini model name"
  type        = string
  default     = "gemini-2.5-flash-native-audio-latest"
}

variable "voice_name" {
  description = "TTS voice name"
  type        = string
  default     = "Aoede"
}

variable "scenario" {
  description = "Case/scenario ID (must match kb/cases/<id> directory)"
  type        = string
  default     = "OSCE_AMALGAM_PREWEDDING_001"
}
