import { supabase } from "@/lib/supabase";
import type { ExtractionResponse, CorrectRequest } from "@/types/nameboard";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function getHeaders(): Promise<HeadersInit> {
  const headers: Record<string, string> = {};

  const { data } = await supabase.auth.getSession();
  if (data.session?.access_token) {
    headers["Authorization"] = `Bearer ${data.session.access_token}`;
  } else {
    const guestSession = sessionStorage.getItem("guest_session");
    if (guestSession) {
      headers["X-Guest-Session"] = guestSession;
    }
  }

  return headers;
}

export async function extractNameboard(files: File[]): Promise<ExtractionResponse> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const headers = await getHeaders();
  const response = await fetch(`${API_URL}/api/nameboard/extract`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Extraction failed");
  }

  return response.json();
}

export async function getExtraction(id: string): Promise<ExtractionResponse> {
  const headers = await getHeaders();
  const response = await fetch(`${API_URL}/api/nameboard/${id}`, { headers });

  if (!response.ok) {
    throw new Error("Failed to load extraction");
  }

  return response.json();
}

export async function acceptExtraction(id: string): Promise<ExtractionResponse> {
  const headers = await getHeaders();
  const response = await fetch(`${API_URL}/api/nameboard/${id}/accept`, {
    method: "POST",
    headers,
  });

  if (!response.ok) throw new Error("Accept failed");
  return response.json();
}

export async function rejectExtraction(id: string): Promise<ExtractionResponse> {
  const headers = await getHeaders();
  const response = await fetch(`${API_URL}/api/nameboard/${id}/reject`, {
    method: "POST",
    headers,
  });

  if (!response.ok) throw new Error("Reject failed");
  return response.json();
}

export async function correctExtraction(
  id: string,
  corrections: CorrectRequest
): Promise<ExtractionResponse> {
  const headers = await getHeaders();
  const response = await fetch(`${API_URL}/api/nameboard/${id}/correct`, {
    method: "POST",
    headers: { ...headers, "Content-Type": "application/json" },
    body: JSON.stringify(corrections),
  });

  if (!response.ok) throw new Error("Correction failed");
  return response.json();
}
