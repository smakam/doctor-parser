export interface ExtractedField {
  value: string | null;
  confidence: number;
  corrected?: boolean;
  _original?: { value: string | null; confidence: number };
}

export interface ExtractedData {
  doctor_name: ExtractedField | null;
  clinic_name: ExtractedField | null;
  specialisation: ExtractedField | null;
  qualifications: ExtractedField | null;
  medical_registration_no: ExtractedField | null;
  address: ExtractedField | null;
  pin_code: ExtractedField | null;
  consultation_timings: ExtractedField | null;
  latitude: number | null;
  longitude: number | null;
  city: string | null;
  state: string | null;
}

export interface ImageQualityResult {
  imagekit_url: string;
  average_word_confidence: number;
  text_density: number;
  quality: "GOOD" | "POOR";
  detected_languages: string[];
  warnings: string[];
}

export interface PiiData {
  phones: string[];
  emails: string[];
}

export interface ExtractionResponse {
  id: string;
  session_id: string;
  images_processed: number;
  overall_confidence: number;
  extracted_data: ExtractedData;
  image_quality: ImageQualityResult[];
  extraction_warnings: string[];
  geocoding_status: string;
  status: string;
  pii_data: PiiData | null;
  created_at: string;
}

export interface CorrectRequest {
  doctor_name?: string;
  clinic_name?: string;
  specialisation?: string;
  qualifications?: string;
  medical_registration_no?: string;
  address?: string;
  pin_code?: string;
  consultation_timings?: string;
}
